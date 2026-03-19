"""Tests for A2A protocol message creation and validation."""

from app.agents.a2a import A2AProtocol
from app.agents.models import A2AMessageType, AgentInsight, AgentOutput


def test_create_task_assignment():
    protocol = A2AProtocol()
    msg = protocol.create_task_assignment(
        source="coordinator",
        target="architecture",
        entities=[{"id": "cls::Foo", "name": "Foo"}],
        relationships=[],
    )
    assert msg.type == A2AMessageType.task_assignment
    assert msg.source_agent == "coordinator"
    assert msg.target_agent == "architecture"
    assert "entities" in msg.payload
    assert msg.correlation_id


def test_create_task_result():
    protocol = A2AProtocol()
    output = AgentOutput(summary="Done", status="success")
    msg = protocol.create_task_result(
        source="architecture",
        target="aggregator",
        output=output,
    )
    assert msg.type == A2AMessageType.task_result
    assert msg.payload["status"] == "success"


def test_create_validation_request():
    protocol = A2AProtocol()
    insight = AgentInsight(
        agent_name="security",
        category="security",
        title="SQL Injection Risk",
        description="Unparameterized query found",
        severity="critical",
        confidence=0.9,
    )
    msg = protocol.create_validation_request(
        source="security",
        target="code_quality",
        insight=insight,
    )
    assert msg.type == A2AMessageType.validation_request
    assert msg.payload["title"] == "SQL Injection Risk"


def test_correlation_chain():
    protocol = A2AProtocol()
    corr_id = "chain-123"

    protocol.create_task_assignment(
        source="coordinator",
        target="arch",
        entities=[],
        relationships=[],
        correlation_id=corr_id,
    )
    protocol.create_task_result(
        source="arch",
        target="aggregator",
        output=AgentOutput(summary="Done", status="success"),
        correlation_id=corr_id,
    )

    chain = protocol.get_message_chain(corr_id)
    assert len(chain) == 2
    assert chain[0].type == A2AMessageType.task_assignment
    assert chain[1].type == A2AMessageType.task_result


def test_get_messages_for_agent():
    protocol = A2AProtocol()
    protocol.create_task_assignment(
        source="coord", target="arch", entities=[], relationships=[]
    )
    protocol.create_task_assignment(
        source="coord", target="security", entities=[], relationships=[]
    )

    arch_msgs = protocol.get_messages_for_agent("arch")
    assert len(arch_msgs) == 1
    assert arch_msgs[0].target_agent == "arch"


def test_context_share():
    protocol = A2AProtocol()
    msg = protocol.create_context_share(
        source="supervisor",
        target="coordinator",
        context={"selected_agents": ["arch", "security"]},
    )
    assert msg.type == A2AMessageType.context_share
    assert msg.payload["selected_agents"] == ["arch", "security"]


def test_clear():
    protocol = A2AProtocol()
    protocol.create_task_assignment(
        source="a", target="b", entities=[], relationships=[]
    )
    assert len(protocol._message_log) == 1
    protocol.clear()
    assert len(protocol._message_log) == 0
