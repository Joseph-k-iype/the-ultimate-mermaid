from app.analyzers.base import PerspectiveAnalyzer
from app.models.domain import CodeEntity, DiagramData, FlowNode, Relationship
from app.utils.determinism import canonical_sort_entities, canonical_sort_relationships

_STRUCTURAL_TYPES = {"class", "model"}
_ER_RELATIONSHIP_TYPES = {"inherits", "uses"}


class ERAnalyzer(PerspectiveAnalyzer):
    """Analyzes entity-relationship structure among classes and models."""

    @property
    def perspective_name(self) -> str:
        return "er"

    def analyze(
        self,
        entities: list[CodeEntity],
        relationships: list[Relationship],
    ) -> DiagramData:
        # Filter structural entities
        structural_entities = [
            e for e in entities if e.entity_type in _STRUCTURAL_TYPES
        ]
        structural_ids = {e.id for e in structural_entities}

        # Include only ER relationships where both endpoints are structural
        er_relationships = [
            rel
            for rel in relationships
            if rel.relationship_type in _ER_RELATIONSHIP_TYPES
            and rel.source_id in structural_ids
            and rel.target_id in structural_ids
        ]

        # Build flow nodes representing ER diagram nodes
        rel_lookup: dict[str, list[str]] = {}
        for rel in er_relationships:
            rel_lookup.setdefault(rel.source_id, []).append(rel.target_id)

        flow_nodes: list[FlowNode] = []
        for entity in structural_entities:
            connections = sorted(rel_lookup.get(entity.id, []))
            flow_nodes.append(
                FlowNode(
                    id=entity.id,
                    label=entity.name,
                    node_type=entity.entity_type,
                    connections=connections,
                )
            )

        flow_nodes.sort(key=lambda n: n.id)

        return DiagramData(
            entities=canonical_sort_entities(structural_entities),
            relationships=canonical_sort_relationships(er_relationships),
            flow_nodes=flow_nodes,
            metadata={"perspective": self.perspective_name},
        )
