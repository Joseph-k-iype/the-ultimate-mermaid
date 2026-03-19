"""Entry point for agent-based analysis of scan results."""

import logging
from datetime import datetime, timezone
from typing import Optional

from app.agents.models import AgentRunResult
from app.agents.state import AgentState
from app.agents.graph.workflow import build_agent_graph

logger = logging.getLogger(__name__)


class AgentOrchestration:
    """
    Main entry point for running multi-agent analysis on completed scans.

    Builds LangGraph state from scan data, runs the compiled graph,
    and returns an AgentRunResult.
    """

    def __init__(self):
        self._graph = None

    def _get_graph(self):
        if self._graph is None:
            self._graph = build_agent_graph()
        return self._graph

    def analyze(self, scan_state) -> AgentRunResult:
        """
        Run agent analysis on a completed scan.

        Args:
            scan_state: The ScanState dataclass from scan_orchestrator

        Returns:
            AgentRunResult with all insights and patterns
        """
        started_at = datetime.now(timezone.utc)

        try:
            # Build LangGraph state from ScanState
            agent_state: AgentState = {
                "scan_id": scan_state.scan_id,
                "entities": [e.model_dump() for e in scan_state.entities],
                "relationships": [
                    r.model_dump() for r in scan_state.relationships
                ],
                "components": scan_state.components,
                "mermaid_code": scan_state.mermaid_code,
                "messages": [],
                "agent_outputs": {},
                "current_task": "starting",
                "retry_count": 0,
                "errors": [],
                "selected_agents": [],
            }

            # Run the graph
            graph = self._get_graph()
            if hasattr(graph, "invoke"):
                final_state = graph.invoke(agent_state)
            else:
                final_state = graph(agent_state)

            # Extract result from final state
            result = final_state.get("result")
            if isinstance(result, AgentRunResult):
                result.started_at = started_at
                result.completed_at = datetime.now(timezone.utc)
                return result

            # If no result in state, build one from agent_outputs
            from app.agents.graph.nodes import aggregator_node

            agg_result = aggregator_node(final_state)
            result = agg_result.get(
                "result",
                AgentRunResult(
                    scan_id=scan_state.scan_id,
                    status="failed",
                    started_at=started_at,
                    completed_at=datetime.now(timezone.utc),
                    errors=["No result produced by agent graph"],
                ),
            )
            if isinstance(result, AgentRunResult):
                result.started_at = started_at
                result.completed_at = datetime.now(timezone.utc)
            return result

        except Exception as exc:
            logger.error(
                f"Agent orchestration failed: {exc}", exc_info=True,
            )
            return AgentRunResult(
                scan_id=getattr(scan_state, "scan_id", "unknown"),
                status="failed",
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
                errors=[str(exc)],
            )


# Singleton
_orchestration: Optional[AgentOrchestration] = None


def get_agent_orchestration() -> AgentOrchestration:
    """Get the AgentOrchestration singleton."""
    global _orchestration
    if _orchestration is None:
        _orchestration = AgentOrchestration()
    return _orchestration


# Convenience alias
agent_orchestration = AgentOrchestration()
