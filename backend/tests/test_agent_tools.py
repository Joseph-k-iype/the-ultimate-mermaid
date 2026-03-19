"""Tests for agent specialist tool functions."""

import json
from unittest.mock import patch, MagicMock

import pytest


MOCK_LLM_RESPONSE = json.dumps({
    "insights": [
        {
            "agent_name": "architecture",
            "category": "architecture",
            "title": "MVC Pattern Detected",
            "description": "The codebase follows MVC architecture",
            "severity": "info",
            "evidence": ["app/routes/ contains controllers", "app/models/ contains models"],
            "recommendations": ["Consider adding a service layer"],
            "confidence": 0.8,
        }
    ],
    "patterns": [
        {
            "pattern_type": "MVC",
            "description": "Model-View-Controller separation",
            "entities_involved": ["ScanRoute", "ScanResponse", "ScanOrchestrator"],
            "confidence": 0.85,
            "related_perspectives": ["architecture"],
        }
    ],
    "summary": "Architecture analysis complete. Found MVC pattern.",
    "status": "success",
})

MOCK_STATE = {
    "scan_id": "test-123",
    "entities": [
        {
            "id": "cls::ScanOrchestrator",
            "name": "ScanOrchestrator",
            "entity_type": "class",
            "file_path": "app/services/scan_orchestrator.py",
            "line_number": 57,
            "metadata": {},
        },
        {
            "id": "endpoint::start_scan",
            "name": "start_scan",
            "entity_type": "endpoint",
            "file_path": "app/routes/scan.py",
            "line_number": 10,
            "metadata": {},
        },
    ],
    "relationships": [
        {
            "source_id": "endpoint::start_scan",
            "target_id": "cls::ScanOrchestrator",
            "relationship_type": "calls",
            "metadata": {},
        }
    ],
    "components": {"services": ["cls::ScanOrchestrator"]},
}


@patch("app.agents.tools._base.get_llm")
def test_analyze_architecture(mock_get_llm):
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MOCK_LLM_RESPONSE
    mock_get_llm.return_value = mock_llm

    from app.agents.tools.architecture_pattern import analyze_architecture

    output = analyze_architecture(MOCK_STATE)
    assert output.status == "success"
    assert len(output.insights) == 1
    assert output.insights[0].title == "MVC Pattern Detected"
    assert len(output.patterns) == 1


@patch("app.agents.tools._base.get_llm")
def test_analyze_security(mock_get_llm):
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = json.dumps({
        "insights": [
            {
                "agent_name": "security",
                "category": "security",
                "title": "Missing CORS Validation",
                "description": "CORS allows all origins",
                "severity": "warning",
                "confidence": 0.7,
            }
        ],
        "patterns": [],
        "summary": "Found 1 security concern",
        "status": "success",
    })
    mock_get_llm.return_value = mock_llm

    from app.agents.tools.security_compliance import analyze_security

    output = analyze_security(MOCK_STATE)
    assert output.status == "success"
    assert output.insights[0].severity == "warning"


@patch("app.agents.tools._base.get_llm")
def test_tool_handles_llm_failure(mock_get_llm):
    from app.agents.llm_adapter import AgentDisabledError

    mock_llm = MagicMock()
    mock_llm.invoke.side_effect = AgentDisabledError("AI not enabled")
    mock_get_llm.return_value = mock_llm

    from app.agents.tools.code_quality import analyze_code_quality

    output = analyze_code_quality(MOCK_STATE)
    assert output.status == "failed"


@patch("app.agents.tools._base.get_llm")
def test_tool_handles_invalid_json(mock_get_llm):
    mock_llm = MagicMock()
    # First call returns invalid JSON, retry returns valid
    mock_llm.invoke.side_effect = [
        "not valid json",
        MOCK_LLM_RESPONSE,
    ]
    mock_get_llm.return_value = mock_llm

    from app.agents.tools.data_flow import analyze_data_flow

    output = analyze_data_flow(MOCK_STATE)
    assert output.status == "success"


@patch("app.agents.tools._base.get_llm")
def test_serialize_context(mock_get_llm):
    from app.agents.tools._base import serialize_context

    context = serialize_context(MOCK_STATE)
    assert "ScanOrchestrator" in context
    assert "calls" in context
    assert "services" in context


def test_tool_registry():
    from app.agents.tools import TOOL_REGISTRY

    assert "data_flow" in TOOL_REGISTRY
    assert "service_flow" in TOOL_REGISTRY
    assert "architecture" in TOOL_REGISTRY
    assert "code_quality" in TOOL_REGISTRY
    assert "security" in TOOL_REGISTRY
    assert "sdlc" in TOOL_REGISTRY
    assert "performance" in TOOL_REGISTRY
    assert len(TOOL_REGISTRY) == 8
