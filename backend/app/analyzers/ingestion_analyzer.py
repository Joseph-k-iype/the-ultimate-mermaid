from app.analyzers.base import PerspectiveAnalyzer
from app.models.domain import CodeEntity, DiagramData, FlowNode, Relationship
from app.utils.determinism import canonical_sort_entities, canonical_sort_relationships

_ENTRY_POINT_TYPES = {"endpoint", "consumer", "file_reader"}
_FORWARD_RELATIONSHIP_TYPES = {"calls", "uses"}


class IngestionAnalyzer(PerspectiveAnalyzer):
    """Analyzes ingestion pipelines by tracing flows from entry-point entities."""

    @property
    def perspective_name(self) -> str:
        return "ingestion"

    def analyze(
        self,
        entities: list[CodeEntity],
        relationships: list[Relationship],
    ) -> DiagramData:
        entity_map = {e.id: e for e in entities}

        # Identify entry-point entities
        entry_points = [e for e in entities if e.entity_type in _ENTRY_POINT_TYPES]
        entry_ids = {e.id for e in entry_points}

        # Build adjacency from forward relationships
        forward_adj: dict[str, list[Relationship]] = {}
        for rel in relationships:
            if rel.relationship_type in _FORWARD_RELATIONSHIP_TYPES:
                forward_adj.setdefault(rel.source_id, []).append(rel)

        # BFS from entry points to find reachable entities
        visited: set[str] = set()
        queue = list(entry_ids)
        relevant_rels: list[Relationship] = []

        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            for rel in forward_adj.get(current, []):
                relevant_rels.append(rel)
                if rel.target_id not in visited:
                    queue.append(rel.target_id)

        # Collect all entities found during traversal
        filtered_entities = [entity_map[eid] for eid in visited if eid in entity_map]

        # Build flow nodes
        flow_nodes: list[FlowNode] = []
        for entity in filtered_entities:
            connections = [
                rel.target_id
                for rel in relevant_rels
                if rel.source_id == entity.id
            ]
            flow_nodes.append(
                FlowNode(
                    id=entity.id,
                    label=entity.name,
                    node_type=entity.entity_type,
                    connections=sorted(connections),
                )
            )

        flow_nodes.sort(key=lambda n: n.id)

        return DiagramData(
            entities=canonical_sort_entities(filtered_entities),
            relationships=canonical_sort_relationships(relevant_rels),
            flow_nodes=flow_nodes,
            metadata={"perspective": self.perspective_name},
        )
