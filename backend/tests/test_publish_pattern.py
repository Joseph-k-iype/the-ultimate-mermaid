"""Tests for perspective-selective pattern publishing."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.scan_orchestrator import ScanState, orchestrator
from app.models.domain import CodeEntity, DiagramData, Relationship
from datetime import datetime, timezone


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_scan():
    """Create a mock completed scan in the orchestrator."""
    scan_id = "test-scan-publish"
    state = ScanState(
        scan_id=scan_id,
        status="completed",
        repo_url="https://github.com/test/repo",
        branch="main",
        created_at=datetime.now(timezone.utc),
        requested_perspectives=["manifest", "er", "dataflow"],
        components={"auth": ["e1", "e2"], "users": ["e3"]},
    )
    state.mermaid_code = {
        "manifest": "flowchart TB\n    A[User]",
        "er": "erDiagram\n    User ||--o{ Post : has",
        "dataflow": "flowchart LR\n    X-->Y",
    }
    orchestrator._scans[scan_id] = state
    yield scan_id
    orchestrator._scans.pop(scan_id, None)


def test_publish_all_perspectives(client, mock_scan):
    resp = client.post(
        f"/api/patterns/from-scan/{mock_scan}",
        json={
            "title": "Test Pattern",
            "description": "A test",
            "owner": "tester",
            "tags": ["test"],
            "perspectives": [],  # empty = all available
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    # Curated content should include ER and Data Flow mermaid blocks
    assert "Entity Relationships" in data["content"]
    assert "Data Flow" in data["content"]
    assert "erDiagram" in data["content"]
    assert "flowchart LR" in data["content"]


def test_publish_selected_perspectives(client, mock_scan):
    resp = client.post(
        f"/api/patterns/from-scan/{mock_scan}",
        json={
            "title": "ER Only",
            "description": "Just ER",
            "owner": "tester",
            "perspectives": ["er"],
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "Entity Relationships" in data["content"]
    assert "erDiagram" in data["content"]
    assert "flowchart LR" not in data["content"]


def test_publish_scan_not_found(client):
    resp = client.post(
        "/api/patterns/from-scan/nonexistent",
        json={
            "title": "Test",
            "description": "Test",
            "owner": "tester",
        },
    )
    assert resp.status_code == 404
