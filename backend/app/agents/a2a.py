"""A2A (Agent-to-Agent) protocol implementation for structured inter-agent communication."""

import logging
from uuid import uuid4

from app.agents.models import (
    A2AMessage,
    A2AMessageType,
    AgentInsight,
    AgentOutput,
)

logger = logging.getLogger(__name__)


class A2AProtocol:
    """
    Implements the Agent-to-Agent protocol for structured message passing.

    Each message carries a correlation_id for tracing message chains
    and a context dict for propagating shared state.
    """

    def __init__(self):
        self._message_log: list[A2AMessage] = []

    def create_task_assignment(
        self,
        source: str,
        target: str,
        entities: list[dict],
        relationships: list[dict],
        correlation_id: str | None = None,
    ) -> A2AMessage:
        """Create a task assignment message from coordinator to specialist."""
        msg = A2AMessage(
            type=A2AMessageType.task_assignment,
            source_agent=source,
            target_agent=target,
            payload={
                "entities": entities,
                "relationships": relationships,
            },
            correlation_id=correlation_id or str(uuid4()),
        )
        self._message_log.append(msg)
        return msg

    def create_task_result(
        self,
        source: str,
        target: str,
        output: AgentOutput,
        correlation_id: str | None = None,
    ) -> A2AMessage:
        """Create a task result message from specialist back to aggregator."""
        msg = A2AMessage(
            type=A2AMessageType.task_result,
            source_agent=source,
            target_agent=target,
            payload=output.model_dump(),
            correlation_id=correlation_id or str(uuid4()),
        )
        self._message_log.append(msg)
        return msg

    def create_validation_request(
        self,
        source: str,
        target: str,
        insight: AgentInsight,
        correlation_id: str | None = None,
    ) -> A2AMessage:
        """Create a validation request for cross-agent verification."""
        msg = A2AMessage(
            type=A2AMessageType.validation_request,
            source_agent=source,
            target_agent=target,
            payload=insight.model_dump(),
            correlation_id=correlation_id or str(uuid4()),
        )
        self._message_log.append(msg)
        return msg

    def create_context_share(
        self,
        source: str,
        target: str,
        context: dict,
        correlation_id: str | None = None,
    ) -> A2AMessage:
        """Create a context sharing message between agents."""
        msg = A2AMessage(
            type=A2AMessageType.context_share,
            source_agent=source,
            target_agent=target,
            payload=context,
            correlation_id=correlation_id or str(uuid4()),
        )
        self._message_log.append(msg)
        return msg

    def get_message_chain(self, correlation_id: str) -> list[A2AMessage]:
        """Get all messages in a correlation chain."""
        return [
            m for m in self._message_log if m.correlation_id == correlation_id
        ]

    def get_messages_for_agent(self, agent_name: str) -> list[A2AMessage]:
        """Get all messages sent to a specific agent."""
        return [
            m for m in self._message_log if m.target_agent == agent_name
        ]

    def clear(self):
        """Clear the message log."""
        self._message_log.clear()


# Module-level singleton
a2a_protocol = A2AProtocol()
