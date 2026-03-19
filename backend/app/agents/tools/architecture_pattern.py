"""Architecture pattern analysis agent tool."""

from app.agents.models import AgentOutput
from app.agents.tools._base import run_agent_tool


def analyze_architecture(state: dict) -> AgentOutput:
    """Detect design patterns and anti-patterns in the codebase."""
    return run_agent_tool(
        "architecture", "architecture", "architecture_pattern.md", state
    )
