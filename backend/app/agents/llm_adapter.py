"""LLM adapter that routes all agent LLM calls through the existing AIService."""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class AgentDisabledError(Exception):
    """Raised when the AI service is not available for agent use."""

    pass


class PatternVizLLM:
    """
    Wraps AIService.call_llm() for use by agent tools.

    Does NOT use LangChain BaseChatModel to avoid unnecessary dependency.
    Instead provides a simple interface that agent tools call directly.
    """

    def __init__(self) -> None:
        self._service = None

    def _get_service(self):
        """Lazily resolve the AIService singleton."""
        if self._service is None:
            try:
                from ai_service import get_ai_service
                self._service = get_ai_service()
            except ImportError:
                raise AgentDisabledError("AIService module not available")
        return self._service

    def invoke(self, system_prompt: str, user_message: str) -> str:
        """
        Call the LLM with a system prompt and user message.

        Routes through AIService.call_llm() which handles JWT auth,
        model selection, and all API defaults.

        Args:
            system_prompt: The system/instruction prompt.
            user_message: The user/context message.

        Returns:
            LLM response text.

        Raises:
            AgentDisabledError: If AI service is not enabled.
        """
        service = self._get_service()

        if not service.is_enabled:
            raise AgentDisabledError("AI service is not enabled")

        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_message})

        return service.call_llm(messages)


# Module-level singleton
_llm: Optional[PatternVizLLM] = None


def get_llm() -> PatternVizLLM:
    """Get the PatternVizLLM singleton."""
    global _llm
    if _llm is None:
        _llm = PatternVizLLM()
    return _llm
