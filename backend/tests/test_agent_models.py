"""Tests for agent Pydantic models."""

import pytest
from datetime import datetime, timezone


def test_agent_insight_valid():
    from app.agents.models import AgentInsight

    insight = AgentInsight(
        agent_name="architecture",
        category="architecture",
        title="Singleton Pattern Detected",
        description="Found singleton pattern in service layer",
        severity="info",
        evidence=["app/services/scan_orchestrator.py:orchestrator"],
        recommendations=["Consider dependency injection for testability"],
        confidence=0.85,
    )
    assert insight.agent_name == "architecture"
    assert insight.confidence == 0.85


def test_agent_insight_invalid_confidence():
    from app.agents.models import AgentInsight

    with pytest.raises(Exception):
        AgentInsight(
            agent_name="test",
            category="architecture",
            title="Test",
            description="Test",
            severity="info",
            confidence=1.5,  # Invalid: > 1.0
        )


def test_agent_output_defaults():
    from app.agents.models import AgentOutput

    output = AgentOutput()
    assert output.insights == []
    assert output.patterns == []
    assert output.summary == ""
    assert output.status == "success"


def test_agent_output_with_insights():
    from app.agents.models import AgentOutput, AgentInsight

    insight = AgentInsight(
        agent_name="security",
        category="security",
        title="Missing Input Validation",
        description="Endpoint lacks request body validation",
        severity="warning",
        confidence=0.9,
    )
    output = AgentOutput(
        insights=[insight],
        summary="Found 1 security issue",
        status="success",
    )
    assert len(output.insights) == 1
    assert output.insights[0].severity == "warning"


def test_detected_pattern():
    from app.agents.models import DetectedPattern

    pattern = DetectedPattern(
        pattern_type="Repository Pattern",
        description="Data access is encapsulated in repository classes",
        entities_involved=["UserRepo", "OrderRepo"],
        confidence=0.75,
        related_perspectives=["architecture", "data_flow"],
    )
    assert pattern.pattern_type == "Repository Pattern"
    assert len(pattern.entities_involved) == 2


def test_agent_run_result():
    from app.agents.models import AgentRunResult

    result = AgentRunResult(
        scan_id="test-scan-123",
        status="success",
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
        agent_summaries={"architecture": "Found 3 patterns"},
    )
    assert result.scan_id == "test-scan-123"
    assert result.status == "success"
    assert result.run_id  # auto-generated


def test_a2a_message():
    from app.agents.models import A2AMessage, A2AMessageType

    msg = A2AMessage(
        type=A2AMessageType.task_assignment,
        source_agent="coordinator",
        target_agent="architecture",
        payload={"entities": []},
    )
    assert msg.type == A2AMessageType.task_assignment
    assert msg.message_id  # auto-generated
    assert msg.correlation_id  # auto-generated
    assert msg.timestamp is not None


def test_a2a_message_types():
    from app.agents.models import A2AMessageType

    assert A2AMessageType.task_assignment == "task_assignment"
    assert A2AMessageType.task_result == "task_result"
    assert A2AMessageType.validation_request == "validation_request"
    assert A2AMessageType.error == "error"
