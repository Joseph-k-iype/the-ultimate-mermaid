"""Security and compliance analysis agent tool."""

from app.agents.models import AgentOutput
from app.agents.tools._base import run_agent_tool


def analyze_security(state: dict) -> AgentOutput:
    """Analyze security vulnerabilities and compliance gaps."""
    return run_agent_tool("security", "security", "security_compliance.md", state)
