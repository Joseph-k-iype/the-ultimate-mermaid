"""Code quality analysis agent tool."""

from app.agents.models import AgentOutput
from app.agents.tools._base import run_agent_tool


def analyze_code_quality(state: dict) -> AgentOutput:
    """Assess code quality and maintainability."""
    return run_agent_tool("code_quality", "code_quality", "code_quality.md", state)
