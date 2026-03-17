"""Tests for graph API endpoints (with FalkorDB unavailable)."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.scan_orchestrator import orchestrator


@pytest.fixture(autouse=True)
def clear_scans():
    """Ensure no leftover scans from other test files affect graph tests."""
    saved = dict(orchestrator._scans)
    orchestrator._scans.clear()
    yield
    orchestrator._scans.clear()
    orchestrator._scans.update(saved)


@pytest.fixture
def client():
    return TestClient(app)


class TestGraphStatus:
    def test_graph_status_returns_available_false(self, client):
        """Without FalkorDB running, status should show unavailable."""
        resp = client.get("/api/graph/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "available" in data
        # FalkorDB not running in test env
        assert data["available"] is False
        assert data["node_count"] == 0

    def test_graph_status_has_details(self, client):
        resp = client.get("/api/graph/status")
        data = resp.json()
        assert "details" in data


class TestKnowledgeGraph:
    def test_knowledge_graph_requires_scan_id(self, client):
        """scan_id is required — omitting it returns 422."""
        resp = client.get("/api/graph/knowledge")
        assert resp.status_code == 422

    def test_knowledge_graph_empty_for_unknown_scan(self, client):
        resp = client.get("/api/graph/knowledge", params={"scan_id": "nonexistent"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["nodes"] == []
        assert data["edges"] == []

    def test_knowledge_graph_scoped_to_scan(self, client):
        """Each scan returns only its own entities."""
        resp = client.get("/api/graph/knowledge", params={"scan_id": "scan-a"})
        data_a = resp.json()
        resp = client.get("/api/graph/knowledge", params={"scan_id": "scan-b"})
        data_b = resp.json()
        # Both empty because neither scan exists, but they should not leak
        assert data_a["nodes"] == []
        assert data_b["nodes"] == []


class TestConceptHierarchy:
    def test_concepts_returns_hierarchy(self, client):
        resp = client.get("/api/graph/concepts")
        assert resp.status_code == 200
        data = resp.json()
        assert "concepts" in data
        concepts = data["concepts"]
        # Should have broader + narrower concepts
        assert len(concepts) > 0
        broader = [c for c in concepts if c["broader"] is None]
        assert len(broader) == 4  # 4 broader concepts

    def test_concept_structure(self, client):
        resp = client.get("/api/graph/concepts")
        concepts = resp.json()["concepts"]
        for c in concepts:
            assert "id" in c
            assert "label" in c
            assert "narrower" in c


class TestRelatedPatterns:
    def test_related_patterns_empty_when_unavailable(self, client):
        resp = client.get("/api/graph/patterns/nonexistent/related")
        assert resp.status_code == 200
        data = resp.json()
        assert data["results"] == []
        assert data["total"] == 0


class TestGraphStats:
    def test_stats_when_unavailable(self, client):
        resp = client.get("/api/graph/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_nodes"] == 0
        assert data["total_edges"] == 0


class TestExistingEndpointsUnaffected:
    """Verify existing endpoints still work with graph integration."""

    def test_scan_list_still_works(self, client):
        resp = client.get("/api/scan")
        assert resp.status_code == 200

    def test_pattern_search_still_works(self, client):
        resp = client.get("/api/patterns")
        assert resp.status_code == 200
        data = resp.json()
        assert "results" in data
        assert "total" in data

    def test_pattern_template_still_works(self, client):
        resp = client.get("/api/patterns/template")
        assert resp.status_code == 200
        assert "content" in resp.json()
