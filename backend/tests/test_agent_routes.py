"""Tests for agent API endpoints."""

from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from app.main import app

    return TestClient(app)


@patch("app.routes.agents.settings")
def test_agents_disabled(mock_settings, client):
    mock_settings.ENABLE_AGENTS = False
    response = client.post("/api/agents/analyze/test-123")
    assert response.status_code == 503
    assert "not enabled" in response.json()["detail"]


@patch("app.routes.agents.settings")
def test_analyze_scan_not_found(mock_settings, client):
    mock_settings.ENABLE_AGENTS = True
    response = client.post("/api/agents/analyze/nonexistent")
    assert response.status_code == 404


@patch("app.routes.agents.settings")
def test_get_insights_disabled(mock_settings, client):
    mock_settings.ENABLE_AGENTS = False
    response = client.get("/api/agents/insights/test-123")
    assert response.status_code == 503


@patch("app.routes.agents.settings")
def test_get_insights_by_invalid_category(mock_settings, client):
    mock_settings.ENABLE_AGENTS = True

    # Mock a completed scan
    from app.services.scan_orchestrator import orchestrator, ScanState

    state = ScanState(
        scan_id="cat-test",
        status="completed",
        repo_url="https://github.com/test/repo",
        branch="main",
        created_at=datetime.now(timezone.utc),
    )
    state.agent_insights = {"insights": [], "patterns": []}
    orchestrator._scans["cat-test"] = state

    response = client.get("/api/agents/insights/cat-test/invalid_category")
    assert response.status_code == 400
    assert "Invalid category" in response.json()["detail"]

    # Cleanup
    del orchestrator._scans["cat-test"]


@patch("app.routes.agents.settings")
def test_get_insights_no_analysis(mock_settings, client):
    mock_settings.ENABLE_AGENTS = True

    from app.services.scan_orchestrator import orchestrator, ScanState

    state = ScanState(
        scan_id="no-insights",
        status="completed",
        repo_url="https://github.com/test/repo",
        branch="main",
        created_at=datetime.now(timezone.utc),
    )
    orchestrator._scans["no-insights"] = state

    response = client.get("/api/agents/insights/no-insights")
    assert response.status_code == 404
    assert "Trigger analysis first" in response.json()["detail"]

    # Cleanup
    del orchestrator._scans["no-insights"]
