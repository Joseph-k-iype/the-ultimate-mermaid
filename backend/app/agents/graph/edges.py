"""Conditional edge routing for the LangGraph workflow."""

import logging

from app.agents.state import AgentState

logger = logging.getLogger(__name__)


def route_to_specialists(state: AgentState) -> list[str]:
    """Return list of specialist node names to fan out to."""
    selected = state.get("selected_agents", [])
    if not selected:
        return ["aggregator"]
    return [f"specialist_{name}" for name in selected]


def should_retry(state: AgentState) -> str:
    """Check if any failed agents should be retried."""
    retry_count = state.get("retry_count", 0)
    errors = state.get("errors", [])

    if errors and retry_count < 1:
        return "retry"
    return "aggregate"
