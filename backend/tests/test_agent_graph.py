"""Tests for LangGraph workflow execution."""

import json
from unittest.mock import patch, MagicMock

import pytest


MOCK_LLM_RESPONSE = json.dumps({
    "insights": [],
    "patterns": [],
    "summary": "Analysis complete",
    "status": "success",
})

MOCK_STATE = {
    "scan_id": "test-graph-123",
    "entities": [
        {"id": "cls::Foo", "name": "Foo", "entity_type": "class", "file_path": "foo.py", "line_number": 1, "metadata": {}},
        {"id": "endpoint::bar", "name": "bar", "entity_type": "endpoint", "file_path": "bar.py", "line_number": 5, "metadata": {}},
        {"id": "fn::baz", "name": "baz", "entity_type": "function", "file_path": "baz.py", "line_number": 10, "metadata": {}},
        {"id": "method::qux", "name": "qux", "entity_type": "method", "file_path": "qux.py", "line_number": 15, "metadata": {}},
        {"id": "model::User", "name": "User", "entity_type": "model", "file_path": "models.py", "line_number": 1, "metadata": {}},
    ],
    "relationships": [],
    "components": {},
    "mermaid_code": {},
    "messages": [],
    "agent_outputs": {},
    "current_task": "",
    "retry_count": 0,
    "errors": [],
    "selected_agents": [],
}


def test_supervisor_node_selects_agents():
    from app.agents.graph.nodes import supervisor_node

    result = supervisor_node(MOCK_STATE)
    selected = result["selected_agents"]
    # Should always include architecture and code_quality
    assert "architecture" in selected
    assert "code_quality" in selected
    # endpoint triggers security and service_flow
    assert "security" in selected
    assert "service_flow" in selected


def test_supervisor_node_minimal_entities():
    from app.agents.graph.nodes import supervisor_node

    state = dict(MOCK_STATE)
    state["entities"] = [
        {"id": "x", "name": "x", "entity_type": "variable", "file_path": "x.py", "line_number": 1}
    ]
    result = supervisor_node(state)
    # With < 5 entities, only basics + mermaid_visualization (always-run)
    assert set(result["selected_agents"]) == {"architecture", "code_quality", "mermaid_visualization"}


def test_coordinator_node():
    from app.agents.graph.nodes import coordinator_node

    state = dict(MOCK_STATE)
    state["selected_agents"] = ["architecture", "code_quality"]
    result = coordinator_node(state)
    assert result["current_task"] == "analyzing"


@patch("app.agents.tools._base.get_llm")
def test_specialist_node(mock_get_llm):
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MOCK_LLM_RESPONSE
    mock_get_llm.return_value = mock_llm

    from app.agents.graph.nodes import specialist_node

    result = specialist_node(MOCK_STATE, "architecture")
    assert "architecture" in result["agent_outputs"]
    assert result["agent_outputs"]["architecture"].status == "success"


def test_specialist_node_unknown_agent():
    from app.agents.graph.nodes import specialist_node

    result = specialist_node(MOCK_STATE, "nonexistent_agent")
    assert result["agent_outputs"]["nonexistent_agent"].status == "failed"


def test_aggregator_node():
    from app.agents.graph.nodes import aggregator_node
    from app.agents.models import AgentOutput, AgentInsight

    state = dict(MOCK_STATE)
    state["agent_outputs"] = {
        "architecture": AgentOutput(
            insights=[
                AgentInsight(
                    agent_name="architecture",
                    category="architecture",
                    title="Pattern Found",
                    description="Test",
                    severity="info",
                    confidence=0.8,
                )
            ],
            summary="Found patterns",
            status="success",
        ),
        "code_quality": AgentOutput(
            summary="Code looks good",
            status="success",
        ),
    }

    result = aggregator_node(state)
    run_result = result["result"]
    assert run_result.status == "success"
    assert len(run_result.insights) == 1
    assert "architecture" in run_result.agent_summaries


def test_aggregator_deduplicates_insights():
    from app.agents.graph.nodes import aggregator_node
    from app.agents.models import AgentOutput, AgentInsight

    duplicate = AgentInsight(
        agent_name="arch",
        category="architecture",
        title="Same Title",
        description="Test",
        severity="info",
        confidence=0.8,
    )
    state = dict(MOCK_STATE)
    state["agent_outputs"] = {
        "a1": AgentOutput(insights=[duplicate], summary="A", status="success"),
        "a2": AgentOutput(insights=[duplicate], summary="B", status="success"),
    }

    result = aggregator_node(state)
    # Should deduplicate by (title, category)
    assert len(result["result"].insights) == 1


@patch("app.agents.tools._base.get_llm")
def test_fallback_runner(mock_get_llm):
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MOCK_LLM_RESPONSE
    mock_get_llm.return_value = mock_llm

    from app.agents.graph.workflow import _fallback_runner

    result = _fallback_runner(MOCK_STATE)
    assert "result" in result
    assert result["result"].scan_id == "test-graph-123"
