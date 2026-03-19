"""Shared helpers for agent tool functions."""

import json
import logging
from pathlib import Path

from app.agents.models import AgentOutput
from app.agents.llm_adapter import get_llm, AgentDisabledError

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def load_prompt(filename: str) -> str:
    """Load a prompt markdown file."""
    path = PROMPTS_DIR / filename
    return path.read_text(encoding="utf-8")


def serialize_context(state: dict, max_entities: int = 200) -> str:
    """Serialize entities and relationships from state into a rich context string."""
    entities = state.get("entities", [])[:max_entities]
    relationships = state.get("relationships", [])
    components = state.get("components", {})
    mermaid_code = state.get("mermaid_code", {})

    parts: list[str] = []

    # Group entities by type for clearer analysis
    by_type: dict[str, list[dict]] = {}
    for e in entities:
        et = e.get("entity_type", "unknown")
        by_type.setdefault(et, []).append(e)

    parts.append("# Codebase Analysis Context")
    parts.append(
        f"Total entities: {len(entities)} | "
        f"Total relationships: {len(relationships)}"
    )
    parts.append(
        "Entity types: "
        + ", ".join(
            f"{k}({len(v)})" for k, v in sorted(by_type.items())
        )
    )
    parts.append("")

    # Classes and Models with full schema
    for et in ("class", "model"):
        group = by_type.get(et, [])
        if not group:
            continue
        parts.append(f"## {et.title()}es ({len(group)})")
        for e in group:
            meta = e.get("metadata", {})
            attrs = meta.get("attributes", [])
            methods = meta.get("methods", [])
            decorators = meta.get("decorators", [])
            line = (
                f"### {e.get('name', '?')} "
                f"({e.get('file_path', '?')}:{e.get('line_number', '?')})"
            )
            parts.append(line)
            if decorators:
                parts.append(
                    f"  Decorators: {', '.join(str(d) for d in decorators)}"
                )
            if attrs:
                parts.append(
                    f"  Attributes: {', '.join(str(a) for a in attrs)}"
                )
            if methods:
                parts.append(
                    f"  Methods: {', '.join(str(m) for m in methods)}"
                )
            parts.append("")

    # Endpoints with HTTP method and route
    endpoints = by_type.get("endpoint", [])
    if endpoints:
        parts.append(f"## Endpoints ({len(endpoints)})")
        for e in endpoints:
            meta = e.get("metadata", {})
            method = meta.get("http_method", "?").upper()
            route = meta.get("route", "?")
            parts.append(
                f"- {method} {route} "
                f"({e.get('file_path', '?')}:{e.get('line_number', '?')})"
            )
        parts.append("")

    # Functions and Methods
    for et in ("function", "method"):
        group = by_type.get(et, [])
        if not group:
            continue
        parts.append(f"## {et.title()}s ({len(group)})")
        for e in group[:80]:  # Cap to avoid token explosion
            meta = e.get("metadata", {})
            decorators = meta.get("decorators", [])
            dec_str = (
                f" [{', '.join(str(d) for d in decorators)}]"
                if decorators
                else ""
            )
            parts.append(
                f"- {e.get('name', '?')}{dec_str} "
                f"({e.get('file_path', '?')}:{e.get('line_number', '?')})"
            )
        if len(group) > 80:
            parts.append(f"  ... and {len(group) - 80} more")
        parts.append("")

    # Data operations
    for et in (
        "db_read",
        "db_write",
        "file_reader",
        "file_writer",
        "consumer",
        "producer",
    ):
        group = by_type.get(et, [])
        if not group:
            continue
        parts.append(
            f"## {et.replace('_', ' ').title()} Operations ({len(group)})"
        )
        for e in group[:50]:
            parts.append(
                f"- {e.get('name', '?')} "
                f"({e.get('file_path', '?')}:{e.get('line_number', '?')})"
            )
        parts.append("")

    # Other entity types not covered above
    covered = {
        "class",
        "model",
        "endpoint",
        "function",
        "method",
        "db_read",
        "db_write",
        "file_reader",
        "file_writer",
        "consumer",
        "producer",
    }
    for et, group in sorted(by_type.items()):
        if et in covered or not group:
            continue
        parts.append(f"## {et.replace('_', ' ').title()} ({len(group)})")
        for e in group[:30]:
            parts.append(
                f"- {e.get('name', '?')} "
                f"({e.get('file_path', '?')}:{e.get('line_number', '?')})"
            )
        parts.append("")

    # Relationships grouped by type
    if relationships:
        rel_by_type: dict[str, list[dict]] = {}
        for r in relationships:
            rt = r.get("relationship_type", "unknown")
            rel_by_type.setdefault(rt, []).append(r)

        parts.append(f"## Relationships ({len(relationships)} total)")
        for rt, rels in sorted(rel_by_type.items()):
            parts.append(f"### {rt} ({len(rels)})")
            for r in rels[:60]:
                src = r.get("source_id", "?")
                if "::" in src:
                    src = src.split("::")[-1]
                tgt = r.get("target_id", "?")
                if "::" in tgt:
                    tgt = tgt.split("::")[-1]
                parts.append(f"- {src} -> {tgt}")
            if len(rels) > 60:
                parts.append(f"  ... and {len(rels) - 60} more")
        parts.append("")

    # Components
    if components:
        parts.append(f"## Components ({len(components)})")
        for name, entity_ids in components.items():
            parts.append(f"- **{name}**: {len(entity_ids)} entities")
        parts.append("")

    # Include mermaid code snippets for structural reference
    for perspective, code in mermaid_code.items():
        if code and len(code) < 3000:
            parts.append(f"## Mermaid Diagram ({perspective})")
            parts.append(f"```mermaid\n{code}\n```")
            parts.append("")

    return "\n".join(parts)


def run_agent_tool(
    agent_name: str,
    category: str,
    prompt_file: str,
    state: dict,
) -> AgentOutput:
    """
    Generic agent tool runner.

    1. Loads prompt
    2. Serializes context
    3. Calls LLM
    4. Parses JSON response
    5. Retries once on parse failure
    6. Returns failed AgentOutput on total failure
    """
    try:
        llm = get_llm()
        system_prompt = load_prompt(prompt_file)
        context = serialize_context(state)

        user_message = (
            f"Analyze the following codebase scan results:\n\n{context}"
        )

        response = llm.invoke(system_prompt, user_message)
        return _parse_response(response, agent_name, category)

    except AgentDisabledError:
        return AgentOutput(
            summary=f"{agent_name} skipped: AI service not available",
            status="failed",
        )
    except Exception as exc:
        # Retry once with error feedback
        try:
            error_msg = (
                f"Previous attempt failed with: {exc}. "
                "Please return valid JSON."
            )
            llm = get_llm()
            system_prompt = load_prompt(prompt_file)
            context = serialize_context(state)
            user_message = (
                f"{error_msg}\n\n"
                f"Analyze the following codebase scan results:\n\n{context}"
            )
            response = llm.invoke(system_prompt, user_message)
            return _parse_response(response, agent_name, category)
        except Exception as retry_exc:
            logger.warning(
                "Agent %s failed after retry: %s", agent_name, retry_exc
            )
            return AgentOutput(
                summary=f"{agent_name} failed: {retry_exc}",
                status="failed",
                insights=[],
                patterns=[],
            )


def _parse_response(
    response: str, agent_name: str, category: str
) -> AgentOutput:
    """Parse LLM JSON response into AgentOutput."""
    text = response.strip()

    # Extract JSON from potential markdown code blocks
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines[1:] if not l.strip().startswith("```")]
        text = "\n".join(lines)

    data = json.loads(text)

    # Ensure agent_name and category are set on all insights
    for insight in data.get("insights", []):
        insight.setdefault("agent_name", agent_name)
        insight.setdefault("category", category)

    return AgentOutput.model_validate(data)
