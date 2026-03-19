"""Agent specialist tool functions."""

from app.agents.tools.data_flow import analyze_data_flow
from app.agents.tools.service_flow import analyze_service_flow
from app.agents.tools.architecture_pattern import analyze_architecture
from app.agents.tools.code_quality import analyze_code_quality
from app.agents.tools.security_compliance import analyze_security
from app.agents.tools.sdlc_mapping import analyze_sdlc
from app.agents.tools.performance_scalability import analyze_performance
from app.agents.tools.mermaid_visualization import analyze_mermaid

TOOL_REGISTRY = {
    "data_flow": analyze_data_flow,
    "service_flow": analyze_service_flow,
    "architecture": analyze_architecture,
    "code_quality": analyze_code_quality,
    "security": analyze_security,
    "sdlc": analyze_sdlc,
    "performance": analyze_performance,
    "mermaid_visualization": analyze_mermaid,
}

__all__ = [
    "analyze_data_flow",
    "analyze_service_flow",
    "analyze_architecture",
    "analyze_code_quality",
    "analyze_security",
    "analyze_sdlc",
    "analyze_performance",
    "analyze_mermaid",
    "TOOL_REGISTRY",
]
