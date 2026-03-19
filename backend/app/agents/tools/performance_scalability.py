"""Performance and scalability analysis agent tool."""

from app.agents.models import AgentOutput
from app.agents.tools._base import run_agent_tool


def analyze_performance(state: dict) -> AgentOutput:
    """Identify performance bottlenecks and scalability issues."""
    return run_agent_tool(
        "performance", "performance", "performance_scalability.md", state
    )
