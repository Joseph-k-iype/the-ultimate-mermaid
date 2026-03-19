"""LangGraph node implementations for agent orchestration."""

import logging
from datetime import datetime, timezone

from app.agents.models import AgentOutput, AgentRunResult
from app.agents.state import AgentState
from app.agents.tools import TOOL_REGISTRY

logger = logging.getLogger(__name__)

# Entity types that suggest each specialist
AGENT_ENTITY_TRIGGERS = {
    "data_flow": {
        "db_read",
        "db_write",
        "file_reader",
        "file_writer",
        "pipeline_stage",
        "pipeline_job",
        "model",
    },
    "service_flow": {"endpoint", "consumer", "producer"},
    "architecture": {"class", "model", "component"},
    "code_quality": {"class", "function", "method"},
    "security": {"endpoint", "db_read", "db_write", "model"},
    "sdlc": {"pipeline_trigger", "pipeline_job", "pipeline_stage"},
    "performance": {"pipeline_stage", "db_read", "db_write", "endpoint"},
}

# These agents always run
ALWAYS_RUN = {"architecture", "code_quality", "mermaid_visualization"}


def supervisor_node(state: AgentState) -> dict:
    """Decide which specialist agents to invoke based on entity types present."""
    entities = state.get("entities", [])
    entity_types = {e.get("entity_type", "") for e in entities}

    selected = set(ALWAYS_RUN)

    for agent_name, trigger_types in AGENT_ENTITY_TRIGGERS.items():
        if entity_types & trigger_types:
            selected.add(agent_name)

    # If very few entities, just run the basics
    if len(entities) < 5:
        selected = set(ALWAYS_RUN)

    logger.info(f"Supervisor selected agents: {selected}")
    return {"selected_agents": sorted(selected), "current_task": "coordinating"}


def coordinator_node(state: AgentState) -> dict:
    """Prepare task context for each selected specialist."""
    selected = state.get("selected_agents", [])
    logger.info(f"Coordinator preparing tasks for: {selected}")
    return {"current_task": "analyzing", "agent_outputs": {}}


def specialist_node(state: AgentState, agent_name: str) -> dict:
    """Run a specific specialist agent tool."""
    logger.info(f"Running specialist: {agent_name}")

    tool_fn = TOOL_REGISTRY.get(agent_name)
    if tool_fn is None:
        logger.warning(f"No tool registered for agent: {agent_name}")
        output = AgentOutput(
            summary=f"No tool found for {agent_name}",
            status="failed",
        )
    else:
        output = tool_fn(state)

    # Merge into existing outputs
    existing = dict(state.get("agent_outputs", {}))
    existing[agent_name] = output
    return {"agent_outputs": existing}


def aggregator_node(state: AgentState) -> dict:
    """Merge all agent outputs into a final AgentRunResult."""
    outputs = state.get("agent_outputs", {})
    scan_id = state.get("scan_id", "unknown")

    all_insights: list = []
    all_patterns: list = []
    agent_summaries: dict[str, str] = {}
    errors: list[str] = []

    for agent_name, output in outputs.items():
        if isinstance(output, AgentOutput):
            all_insights.extend(output.insights)
            all_patterns.extend(output.patterns)
            agent_summaries[agent_name] = output.summary
            if output.status == "failed":
                errors.append(f"{agent_name}: {output.summary}")
        elif isinstance(output, dict):
            # Handle dict form
            try:
                parsed = AgentOutput.model_validate(output)
                all_insights.extend(parsed.insights)
                all_patterns.extend(parsed.patterns)
                agent_summaries[agent_name] = parsed.summary
                if parsed.status == "failed":
                    errors.append(f"{agent_name}: {parsed.summary}")
            except Exception as exc:
                errors.append(f"{agent_name}: failed to parse output - {exc}")

    # Deduplicate insights by title
    seen_titles: set[tuple[str, str]] = set()
    unique_insights = []
    for insight in all_insights:
        key = (insight.title, insight.category)
        if key not in seen_titles:
            seen_titles.add(key)
            unique_insights.append(insight)

    # Determine overall status
    total = len(outputs)
    failed = len(errors)
    if failed == 0:
        status = "success"
    elif failed < total:
        status = "partial"
    else:
        status = "failed"

    result = AgentRunResult(
        scan_id=scan_id,
        status=status,
        started_at=datetime.now(timezone.utc),  # approximate
        completed_at=datetime.now(timezone.utc),
        insights=unique_insights,
        patterns=all_patterns,
        agent_summaries=agent_summaries,
        errors=errors,
    )

    return {"result": result}
