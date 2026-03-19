"""Tests for the end-to-end data flow analyzer."""

import pytest

from app.analyzers.dataflow_analyzer import DataFlowAnalyzer
from app.models.domain import CodeEntity, Relationship


@pytest.fixture
def analyzer():
    return DataFlowAnalyzer()


def _entity(eid: str, name: str, etype: str, fp: str = "app.py") -> CodeEntity:
    return CodeEntity(id=eid, name=name, entity_type=etype, file_path=fp, line_number=1)


class TestEndToEndTracing:
    """Core path-tracing tests: entry → ... → exit."""

    def test_complete_path_entry_to_exit(self, analyzer):
        entities = [
            _entity("e1", "POST /orders", "endpoint"),
            _entity("f1", "validate", "function"),
            _entity("f2", "save_order", "function"),
            _entity("db1", "db.commit", "db_write"),
        ]
        relationships = [
            Relationship(source_id="e1", target_id="f1", relationship_type="calls"),
            Relationship(source_id="f1", target_id="f2", relationship_type="calls"),
            Relationship(source_id="f2", target_id="db1", relationship_type="writes"),
        ]
        result = analyzer.analyze(entities, relationships)
        node_ids = {n.id for n in result.flow_nodes}
        # All four nodes are on the entry→exit path
        assert node_ids == {"e1", "f1", "f2", "db1"}

    def test_dead_end_branch_included(self, analyzer):
        """A node reachable from entry is included even if it does not lead to exit."""
        entities = [
            _entity("e1", "GET /users", "endpoint"),
            _entity("f1", "get_users", "function"),
            _entity("f2", "log_request", "function"),  # dead end — no exit
            _entity("db1", "db.query", "db_write"),
        ]
        relationships = [
            Relationship(source_id="e1", target_id="f1", relationship_type="calls"),
            Relationship(source_id="e1", target_id="f2", relationship_type="calls"),
            Relationship(source_id="f1", target_id="db1", relationship_type="writes"),
        ]
        result = analyzer.analyze(entities, relationships)
        node_ids = {n.id for n in result.flow_nodes}
        # All relationship participants are included
        assert node_ids == {"e1", "f1", "f2", "db1"}

    def test_multiple_relationship_types(self, analyzer):
        """All data-movement relationship types are traversed."""
        entities = [
            _entity("e1", "handle", "endpoint"),
            _entity("f1", "process", "function"),
            _entity("db1", "db.query", "db_read"),
            _entity("db2", "db.insert", "db_write"),
            _entity("p1", "kafka.send", "producer"),
        ]
        relationships = [
            Relationship(source_id="e1", target_id="f1", relationship_type="calls"),
            Relationship(source_id="f1", target_id="db1", relationship_type="reads"),
            Relationship(source_id="f1", target_id="db2", relationship_type="writes"),
            Relationship(source_id="f1", target_id="p1", relationship_type="produces"),
        ]
        result = analyzer.analyze(entities, relationships)
        node_ids = {n.id for n in result.flow_nodes}
        assert node_ids == {"e1", "f1", "db1", "db2", "p1"}

    def test_file_reader_as_entry(self, analyzer):
        """file_reader counts as an entry point."""
        entities = [
            _entity("fr1", "read_csv", "file_reader"),
            _entity("f1", "parse", "function"),
            _entity("db1", "db.save", "db_write"),
        ]
        relationships = [
            Relationship(source_id="fr1", target_id="f1", relationship_type="calls"),
            Relationship(source_id="f1", target_id="db1", relationship_type="writes"),
        ]
        result = analyzer.analyze(entities, relationships)
        node_ids = {n.id for n in result.flow_nodes}
        assert node_ids == {"fr1", "f1", "db1"}


class TestNodeClassification:
    def test_node_types(self, analyzer):
        entities = [
            _entity("e1", "POST /data", "endpoint"),
            _entity("f1", "transform", "function"),
            _entity("db1", "db.write", "db_write"),
        ]
        relationships = [
            Relationship(source_id="e1", target_id="f1", relationship_type="calls"),
            Relationship(source_id="f1", target_id="db1", relationship_type="writes"),
        ]
        result = analyzer.analyze(entities, relationships)
        type_map = {n.id: n.node_type for n in result.flow_nodes}
        assert type_map["e1"] == "entry"
        assert type_map["f1"] == "transform"
        assert type_map["db1"] == "exit"


class TestFallbacks:
    def test_empty_input(self, analyzer):
        result = analyzer.analyze([], [])
        assert result.flow_nodes == []
        assert result.entities == []

    def test_no_entry_exit_falls_back_to_participants(self, analyzer):
        """When no entry/exit points, include all relationship participants."""
        entities = [
            _entity("f1", "process", "function"),
            _entity("f2", "transform", "function"),
        ]
        relationships = [
            Relationship(source_id="f1", target_id="f2", relationship_type="calls"),
        ]
        result = analyzer.analyze(entities, relationships)
        node_ids = {n.id for n in result.flow_nodes}
        assert "f1" in node_ids
        assert "f2" in node_ids

    def test_passes_data_traversed(self, analyzer):
        entities = [
            _entity("e1", "handle_request", "endpoint"),
            _entity("f1", "validate", "function"),
            _entity("f2", "save", "function"),
            _entity("db1", "db.commit", "db_write"),
        ]
        relationships = [
            Relationship(source_id="e1", target_id="f1", relationship_type="passes_data",
                         metadata={"param": "data"}),
            Relationship(source_id="f1", target_id="f2", relationship_type="passes_data",
                         metadata={"param": "validated"}),
            Relationship(source_id="f2", target_id="db1", relationship_type="writes"),
        ]
        result = analyzer.analyze(entities, relationships)
        node_ids = {n.id for n in result.flow_nodes}
        assert node_ids == {"e1", "f1", "f2", "db1"}
