"""Data flow analysis agent tool."""

from app.agents.models import AgentOutput
from app.agents.tools._base import run_agent_tool


def analyze_data_flow(state: dict) -> AgentOutput:
    """Analyze data movement patterns in the codebase."""
    return run_agent_tool("data_flow", "data_flow", "data_flow.md", state)
