import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.pattern_service import pattern_service


@pytest.fixture(autouse=True)
def clear_patterns():
    """Clear pattern store before each test."""
    pattern_service._patterns.clear()
    yield
    pattern_service._patterns.clear()


@pytest.fixture
def client():
    return TestClient(app)


def _create_payload(**overrides):
    defaults = {
        "title": "Auth Pattern",
        "description": "JWT-based authentication",
        "owner": "platform-team",
        "tags": ["auth", "security"],
        "content": "# Auth\n\nUse JWT tokens.",
    }
    defaults.update(overrides)
    return defaults


class TestCreatePattern:
    def test_create_pattern(self, client):
        resp = client.post("/api/patterns", json=_create_payload())
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Auth Pattern"
        assert data["owner"] == "platform-team"
        assert data["status"] == "draft"
        assert data["version"] == 1
        assert "auth" in data["tags"]
        assert data["id"]

    def test_create_pattern_with_mermaid(self, client):
        content = "# Arch\n\n```mermaid\ngraph TD\n    A-->B\n```\n\nDone."
        resp = client.post("/api/patterns", json=_create_payload(content=content))
        assert resp.status_code == 201
        data = resp.json()
        assert len(data["mermaid_diagrams"]) == 1
        assert "graph TD" in data["mermaid_diagrams"][0]


class TestGetPattern:
    def test_get_pattern(self, client):
        create_resp = client.post("/api/patterns", json=_create_payload())
        pid = create_resp.json()["id"]

        resp = client.get(f"/api/patterns/{pid}")
        assert resp.status_code == 200
        assert resp.json()["id"] == pid

    def test_get_pattern_not_found(self, client):
        resp = client.get("/api/patterns/nonexistent")
        assert resp.status_code == 404


class TestUpdatePattern:
    def test_update_pattern(self, client):
        create_resp = client.post("/api/patterns", json=_create_payload())
        pid = create_resp.json()["id"]

        resp = client.put(f"/api/patterns/{pid}", json={"title": "Updated Auth"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Updated Auth"
        assert data["version"] == 2

    def test_update_not_found(self, client):
        resp = client.put("/api/patterns/nonexistent", json={"title": "X"})
        assert resp.status_code == 404


class TestDeletePattern:
    def test_delete_pattern(self, client):
        create_resp = client.post("/api/patterns", json=_create_payload())
        pid = create_resp.json()["id"]

        resp = client.delete(f"/api/patterns/{pid}")
        assert resp.status_code == 204

        resp = client.get(f"/api/patterns/{pid}")
        assert resp.status_code == 404

    def test_delete_not_found(self, client):
        resp = client.delete("/api/patterns/nonexistent")
        assert resp.status_code == 404


class TestSearchPatterns:
    def _seed(self, client):
        client.post("/api/patterns", json=_create_payload())
        client.post(
            "/api/patterns",
            json=_create_payload(
                title="CQRS Pattern",
                description="Command Query Responsibility Segregation",
                owner="backend-team",
                tags=["architecture", "cqrs"],
                content="# CQRS\n\nSeparate reads from writes.",
            ),
        )

    def test_search_by_text(self, client):
        self._seed(client)
        resp = client.get("/api/patterns", params={"query": "JWT"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["results"][0]["title"] == "Auth Pattern"

    def test_search_by_tags(self, client):
        self._seed(client)
        resp = client.get("/api/patterns", params={"tags": ["architecture"]})
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_search_by_status(self, client):
        self._seed(client)
        resp = client.get("/api/patterns", params={"status": "draft"})
        assert resp.status_code == 200
        assert resp.json()["total"] == 2

    def test_search_by_owner(self, client):
        self._seed(client)
        resp = client.get("/api/patterns", params={"owner": "backend-team"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["results"][0]["owner"] == "backend-team"

    def test_combined_search_filters(self, client):
        self._seed(client)
        resp = client.get(
            "/api/patterns",
            params={"query": "CQRS", "owner": "backend-team", "status": "draft"},
        )
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_search_returns_all_when_no_filters(self, client):
        self._seed(client)
        resp = client.get("/api/patterns")
        assert resp.status_code == 200
        assert resp.json()["total"] == 2


class TestSystemDesignTemplate:
    def test_get_system_design_template(self, client):
        resp = client.get("/api/patterns/template")
        assert resp.status_code == 200
        content = resp.json()["content"]
        assert "## Overview" in content
        assert "```mermaid" in content


class TestStatusTransition:
    def test_status_transition_valid(self, client):
        create_resp = client.post("/api/patterns", json=_create_payload())
        pid = create_resp.json()["id"]

        # draft -> review
        resp = client.post(f"/api/patterns/{pid}/transition", json={"status": "review"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "review"

        # review -> approved
        resp = client.post(f"/api/patterns/{pid}/transition", json={"status": "approved"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "approved"

    def test_status_transition_invalid(self, client):
        create_resp = client.post("/api/patterns", json=_create_payload())
        pid = create_resp.json()["id"]

        # draft -> approved (not allowed)
        resp = client.post(f"/api/patterns/{pid}/transition", json={"status": "approved"})
        assert resp.status_code == 400


class TestMermaidExtraction:
    def test_mermaid_extraction(self, client):
        content = (
            "# Design\n\n"
            "```mermaid\ngraph TD\n    A-->B\n```\n\n"
            "Some text.\n\n"
            "```mermaid\nsequenceDiagram\n    A->>B: Hello\n```"
        )
        resp = client.post("/api/patterns", json=_create_payload(content=content))
        assert resp.status_code == 201
        diagrams = resp.json()["mermaid_diagrams"]
        assert len(diagrams) == 2
        assert "graph TD" in diagrams[0]
        assert "sequenceDiagram" in diagrams[1]
