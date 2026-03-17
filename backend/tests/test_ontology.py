"""Tests for the SKOS ontology definitions."""

from app.graph.ontology import (
    ALL_ENTITY_TYPES,
    CODE_RELATIONSHIP_TYPES,
    CONCEPT_HIERARCHY,
    ENTITY_TO_CONCEPT,
    PERSPECTIVE_DEFINITIONS,
    EntityClass,
    OntologyRelationType,
)


class TestEntityClassEnum:
    def test_all_leaf_types_have_broader_concept(self):
        """Every concrete entity_type must map to a broader SKOS concept."""
        leaf_types = {
            "class", "function", "method", "variable",
            "endpoint", "model",
            "db_read", "db_write", "file_reader", "file_writer",
            "consumer", "producer",
        }
        for et in leaf_types:
            assert et in ENTITY_TO_CONCEPT, f"{et} missing from ENTITY_TO_CONCEPT"

    def test_broader_concepts_exist_in_enum(self):
        for broader in CONCEPT_HIERARCHY:
            assert broader in [e.value for e in EntityClass]

    def test_no_orphan_entity_types(self):
        """ALL_ENTITY_TYPES should match exactly the leaf types in hierarchy."""
        from_hierarchy = set()
        for narrower_list in CONCEPT_HIERARCHY.values():
            from_hierarchy.update(narrower_list)
        assert ALL_ENTITY_TYPES == from_hierarchy


class TestOntologyRelationType:
    def test_code_relationships_defined(self):
        expected = {"calls", "inherits", "imports", "uses", "contains",
                    "produces", "consumes", "reads", "writes"}
        assert CODE_RELATIONSHIP_TYPES == expected

    def test_all_code_rels_in_enum(self):
        for rel in CODE_RELATIONSHIP_TYPES:
            assert rel in [r.value for r in OntologyRelationType]

    def test_semantic_relations_in_enum(self):
        for rel in ("broader", "narrower", "related"):
            assert rel in [r.value for r in OntologyRelationType]

    def test_metadata_relations_in_enum(self):
        for rel in ("has_tag", "belongs_to_scan", "linked_to_pattern"):
            assert rel in [r.value for r in OntologyRelationType]


class TestConceptHierarchy:
    def test_hierarchy_is_complete(self):
        assert len(CONCEPT_HIERARCHY) == 4
        assert set(CONCEPT_HIERARCHY.keys()) == {
            "CodeConstruct", "APIElement", "DataAccessor", "MessageHandler",
        }

    def test_no_circular_references(self):
        """A narrower type should not also appear as a broader concept."""
        all_broader = set(CONCEPT_HIERARCHY.keys())
        all_narrower = set()
        for narrower_list in CONCEPT_HIERARCHY.values():
            all_narrower.update(narrower_list)
        assert not (all_broader & all_narrower), "Circular reference detected"

    def test_all_narrower_are_unique(self):
        all_narrower = []
        for narrower_list in CONCEPT_HIERARCHY.values():
            all_narrower.extend(narrower_list)
        assert len(all_narrower) == len(set(all_narrower)), "Duplicate narrower type"


class TestPerspectiveDefinitions:
    def test_all_four_perspectives_defined(self):
        assert set(PERSPECTIVE_DEFINITIONS.keys()) == {
            "er", "ingestion", "transformation", "output",
        }

    def test_er_types(self):
        defn = PERSPECTIVE_DEFINITIONS["er"]
        assert "class" in defn.entity_types
        assert "model" in defn.entity_types
        assert "inherits" in defn.relationship_types

    def test_ingestion_types(self):
        defn = PERSPECTIVE_DEFINITIONS["ingestion"]
        assert "endpoint" in defn.entity_types
        assert "consumer" in defn.entity_types
        assert "reads" in defn.relationship_types

    def test_transformation_types(self):
        defn = PERSPECTIVE_DEFINITIONS["transformation"]
        assert "function" in defn.entity_types
        assert "db_read" in defn.entity_types
        assert "writes" in defn.relationship_types

    def test_output_types(self):
        defn = PERSPECTIVE_DEFINITIONS["output"]
        assert "producer" in defn.entity_types
        assert "db_write" in defn.entity_types
        assert "produces" in defn.relationship_types

    def test_all_entity_types_valid(self):
        """Every entity_type in a perspective must be a known leaf type."""
        for defn in PERSPECTIVE_DEFINITIONS.values():
            for et in defn.entity_types:
                assert et in ALL_ENTITY_TYPES, (
                    f"Unknown entity_type '{et}' in perspective '{defn.name}'"
                )

    def test_all_relationship_types_valid(self):
        """Every relationship_type in a perspective must be a known code rel."""
        for defn in PERSPECTIVE_DEFINITIONS.values():
            for rt in defn.relationship_types:
                assert rt in CODE_RELATIONSHIP_TYPES, (
                    f"Unknown rel_type '{rt}' in perspective '{defn.name}'"
                )
