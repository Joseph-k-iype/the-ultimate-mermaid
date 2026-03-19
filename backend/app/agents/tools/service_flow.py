"""Service flow analysis agent tool."""

from app.agents.models import AgentOutput
from app.agents.tools._base import run_agent_tool


def analyze_service_flow(state: dict) -> AgentOutput:
    """Analyze service interaction patterns in the codebase."""
    return run_agent_tool("service_flow", "service_flow", "service_flow.md", state)
