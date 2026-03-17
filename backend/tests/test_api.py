import tempfile
from pathlib import Path
from unittest.mock import patch


def _create_sample_repo(tmp_dir: str) -> Path:
    """Create a temp dir with sample Python files for testing."""
    p = Path(tmp_dir)
    sample = p / "app.py"
    sample.write_text(
        'class User:\n    name: str\n\n@app.get("/users")\ndef get_users():\n    pass\n'
    )
    return p


class TestScanAPI:
    def test_create_scan(self, client):
        with tempfile.TemporaryDirectory() as tmp:
            sample_path = _create_sample_repo(tmp)
            with patch(
                "app.services.scan_orchestrator.RepoService.clone_repo",
                return_value=sample_path,
            ), patch(
                "app.services.scan_orchestrator.RepoService.cleanup",
            ):
                resp = client.post(
                    "/api/scan",
                    json={"repo_url": "https://github.com/test/repo.git", "branch": "main"},
                )
                assert resp.status_code == 200
                data = resp.json()
                assert data["status"] == "completed"
                assert data["scan_id"]

    def test_get_scan_not_found(self, client):
        resp = client.get("/api/scan/nonexistent")
        assert resp.status_code == 404

    def test_get_diagram(self, client):
        with tempfile.TemporaryDirectory() as tmp:
            sample_path = _create_sample_repo(tmp)
            with patch(
                "app.services.scan_orchestrator.RepoService.clone_repo",
                return_value=sample_path,
            ), patch(
                "app.services.scan_orchestrator.RepoService.cleanup",
            ):
                resp = client.post(
                    "/api/scan",
                    json={"repo_url": "https://github.com/test/repo.git", "branch": "main"},
                )
                scan_id = resp.json()["scan_id"]

                for perspective in ("ingestion", "er", "transformation", "output"):
                    resp = client.get(f"/api/scan/{scan_id}/diagrams/{perspective}")
                    assert resp.status_code == 200
                    data = resp.json()
                    assert data["perspective"] == perspective
                    assert data["mermaid_code"]

    def test_invalid_perspective(self, client):
        resp = client.get("/api/scan/someid/diagrams/invalid")
        assert resp.status_code == 400


class TestTemplateAPI:
    def test_create_and_get_template(self, client):
        resp = client.post(
            "/api/templates",
            json={
                "name": "Test Template",
                "perspective": "er",
                "template_content": "erDiagram\n    {{ entity_name }} {\n    }",
                "placeholders": ["entity_name"],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        template_id = data["id"]
        assert data["name"] == "Test Template"

        resp = client.get(f"/api/templates/{template_id}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Test Template"

    def test_list_templates(self, client):
        resp = client.get("/api/templates")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_render_template(self, client):
        resp = client.post(
            "/api/templates",
            json={
                "name": "Render Test",
                "perspective": "er",
                "template_content": "erDiagram\n    {{ name }} {\n    }",
                "placeholders": ["name"],
            },
        )
        template_id = resp.json()["id"]

        resp = client.post(
            f"/api/templates/{template_id}/render",
            json={"template_id": template_id, "values": {"name": "MyEntity"}},
        )
        assert resp.status_code == 200
        rendered = resp.json()["rendered"]
        assert "MyEntity" in rendered

    def test_delete_template(self, client):
        resp = client.post(
            "/api/templates",
            json={
                "name": "To Delete",
                "perspective": "er",
                "template_content": "test",
                "placeholders": [],
            },
        )
        template_id = resp.json()["id"]

        resp = client.delete(f"/api/templates/{template_id}")
        assert resp.status_code == 204

        resp = client.get(f"/api/templates/{template_id}")
        assert resp.status_code == 404

    def test_template_not_found(self, client):
        resp = client.get("/api/templates/nonexistent")
        assert resp.status_code == 404
