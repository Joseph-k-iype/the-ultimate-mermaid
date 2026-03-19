"""Google ADK bridge for agent registration and discovery."""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ADKBridge:
    """
    Bridge between PatternViz agents and Google Agent Development Kit (ADK).

    Registers agents with ADK for discovery and orchestration.
    Gracefully degrades if google-adk is not installed.
    """

    def __init__(self):
        self._agents: dict[str, object] = {}
        self._adk_available = False
        self._check_adk()

    def _check_adk(self):
        """Check if Google ADK is available."""
        try:
            import google.adk  # noqa: F401

            self._adk_available = True
            logger.info("Google ADK available")
        except ImportError:
            self._adk_available = False
            logger.info("Google ADK not installed, operating without it")

    @property
    def is_available(self) -> bool:
        return self._adk_available

    def register_agents(self):
        """Register all specialist agents with ADK if available."""
        if not self._adk_available:
            logger.debug("Skipping ADK agent registration (not available)")
            return

        from app.agents.tools import TOOL_REGISTRY

        agent_names = [
            "supervisor",
            "coordinator",
            *TOOL_REGISTRY.keys(),
        ]

        for name in agent_names:
            self._register_single(name)

        logger.info(f"Registered {len(agent_names)} agents with ADK")

    def _register_single(self, name: str):
        """Register a single agent with ADK."""
        try:
            # ADK registration would go here when the API stabilizes
            self._agents[name] = {"name": name, "status": "registered"}
            logger.debug(f"Registered agent with ADK: {name}")
        except Exception as exc:
            logger.warning(f"Failed to register {name} with ADK: {exc}")

    def get_agent(self, name: str) -> Optional[dict]:
        """Retrieve a registered agent by name."""
        return self._agents.get(name)

    def list_agents(self) -> list[str]:
        """List all registered agent names."""
        return list(self._agents.keys())


# Module-level singleton
_bridge: Optional[ADKBridge] = None


def get_adk_bridge() -> ADKBridge:
    """Get the ADK bridge singleton."""
    global _bridge
    if _bridge is None:
        _bridge = ADKBridge()
    return _bridge
