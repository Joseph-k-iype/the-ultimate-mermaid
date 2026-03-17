"""Tests for GraphService with mocked FalkorDB."""

from unittest.mock import MagicMock, patch

import pytest

from app.graph.graph_service import GraphService
from app.models.domain import CodeEntity, Relationship
from app.models.pattern import PatternModel, PatternStatus


@pytest.fixture
def service():
    """A fresh GraphService instance (not connected)."""
    return GraphService()


@pytest.fixture
def mock_entity():
    return CodeEntity(
        id="app.py::UserModel",
        name="UserModel",
        entity_type="class",
        file_path="app.py",
        line_number=1,
    )


@pytest.fixture
def mock_pattern():
    return PatternModel(
        id="pattern-1",
        title="Auth Pattern",
        description="JWT auth",
        owner="team",
        status=PatternStatus.draft,
        tags=["CodeConstruct"],
        content="# Auth",
    )


class TestAvailability:
    def test_not_available_by_default(self, service):
        assert service.is_available is False

    def test_not_available_when_connection_fails(self, service):
        service.connect("nonexistent-host", 9999, "test")
        assert service.is_available is False

    def test_all_methods_safe_when_unavailable(self, service, mock_entity, mock_pattern):
        """All methods should return None/empty without raising."""
        service.initialize_schema()
        service.store_entities("scan-1", [mock_entity])
        service.store_relationships([])
        service.store_pattern(mock_pattern)
        service.update_pattern("p1", {"title": "X"})
        service.delete_pattern("p1")
        assert service.query_perspective("scan-1", "er") is None
        assert service.search_patterns() is None
        assert service.find_related_patterns("p1") == []
        assert service.get_knowledge_graph() == {"nodes": [], "edges": []}
        stats = service.get_stats()
        assert stats["total_nodes"] == 0


class TestWithMockedGraph:
    @pytest.fixture
    def connected_service(self):
        service = GraphService()
        service._available = True
        service._graph = MagicMock()
        # Default: query returns empty result set
        mock_result = MagicMock()
        mock_result.result_set = []
        service._graph.query.return_value = mock_result
        return service

    def test_initialize_schema_creates_indexes(self, connected_service):
        connected_service.initialize_schema()
        assert connected_service._graph.query.call_count > 0

    def test_store_entities_calls_query(self, connected_service, mock_entity):
        connected_service.store_entities("scan-1", [mock_entity])
        # Should have MERGE Scan + MERGE entity + BELONGS_TO_SCAN + HAS_TAG
        assert connected_service._graph.query.call_count >= 3

    def test_store_relationships_creates_edges(self, connected_service):
        rel = Relationship(
            source_id="a", target_id="b", relationship_type="calls"
        )
        connected_service.store_relationships([rel])
        # Verify a query was made with CALLS relationship type
        calls = connected_service._graph.query.call_args_list
        found = any("CALLS" in str(c) for c in calls)
        assert found

    def test_store_pattern(self, connected_service, mock_pattern):
        connected_service.store_pattern(mock_pattern)
        assert connected_service._graph.query.call_count >= 1

    def test_delete_pattern(self, connected_service):
        connected_service.delete_pattern("p1")
        calls = connected_service._graph.query.call_args_list
        found = any("DETACH DELETE" in str(c) for c in calls)
        assert found

    def test_query_perspective_returns_diagram_data(self, connected_service):
        # Mock entity results
        entity_result = MagicMock()
        entity_result.result_set = [
            ("id1", "MyClass", "class", "app.py", 1),
            ("id2", "MyModel", "model", "app.py", 10),
        ]
        rel_result = MagicMock()
        rel_result.result_set = [
            ("id1", "id2", "USES"),
        ]
        connected_service._graph.query.side_effect = [entity_result, rel_result]

        result = connected_service.query_perspective("scan-1", "er")
        assert result is not None
        assert len(result.entities) == 2
        assert len(result.relationships) == 1
        assert result.metadata["perspective"] == "er"

    def test_query_perspective_unknown_returns_none(self, connected_service):
        result = connected_service.query_perspective("scan-1", "nonexistent")
        assert result is None

    def test_search_patterns_with_tags(self, connected_service):
        mock_result = MagicMock()
        mock_result.result_set = [
            ("p1", "Auth", "JWT auth", "team", "draft", 1),
        ]
        connected_service._graph.query.return_value = mock_result

        results = connected_service.search_patterns(tags=["CodeConstruct"])
        assert results is not None
        assert len(results) == 1
        assert results[0]["id"] == "p1"

    def test_find_related_patterns(self, connected_service):
        mock_result = MagicMock()
        mock_result.result_set = [
            ("p2", "Related", "A related pattern", "team", "draft", 1),
        ]
        connected_service._graph.query.return_value = mock_result

        results = connected_service.find_related_patterns("p1")
        assert len(results) == 1
        assert results[0]["id"] == "p2"

    def test_get_knowledge_graph_with_scan_id(self, connected_service):
        node_result = MagicMock()
        node_result.result_set = [
            ("id1", "MyClass", "class", "CodeEntity"),
        ]
        edge_result = MagicMock()
        edge_result.result_set = []
        connected_service._graph.query.side_effect = [node_result, edge_result]

        result = connected_service.get_knowledge_graph(scan_id="scan-1")
        assert len(result["nodes"]) == 1
        assert result["nodes"][0]["id"] == "id1"

    def test_get_concepts_returns_hierarchy(self, connected_service):
        concepts = connected_service.get_concepts()
        broader_names = [c["id"] for c in concepts if c["broader"] is None]
        assert "CodeConstruct" in broader_names
        assert "APIElement" in broader_names

    def test_query_handles_graph_error(self, connected_service):
        connected_service._graph.query.side_effect = Exception("Connection lost")
        # Should not raise, just return None
        result = connected_service._query("RETURN 1")
        assert result is None
