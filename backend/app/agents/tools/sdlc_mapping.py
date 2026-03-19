"""SDLC mapping analysis agent tool."""

from app.agents.models import AgentOutput
from app.agents.tools._base import run_agent_tool


def analyze_sdlc(state: dict) -> AgentOutput:
    """Map code structure to SDLC phases."""
    return run_agent_tool("sdlc", "sdlc", "sdlc_mapping.md", state)
