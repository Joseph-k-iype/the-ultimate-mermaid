from app.analyzers.base import PerspectiveAnalyzer
from app.models.domain import CodeEntity, DiagramData, FlowNode, Relationship
from app.utils.determinism import canonical_sort_entities, canonical_sort_relationships

_SINK_TYPES = {"producer", "file_writer", "db_write"}
_INBOUND_RELATIONSHIP_TYPES = {"calls", "uses", "produces", "writes"}


class OutputAnalyzer(PerspectiveAnalyzer):
    """Analyzes output pipelines by tracing flows into sink entities."""

    @property
    def perspective_name(self) -> str:
        return "output"

    def analyze(
        self,
        entities: list[CodeEntity],
        relationships: list[Relationship],
    ) -> DiagramData:
        entity_map = {e.id: e for e in entities}

        # Identify sink entities
        sinks = [e for e in entities if e.entity_type in _SINK_TYPES]
        sink_ids = {e.id for e in sinks}

        # Build reverse adjacency for backward traversal
        reverse_adj: dict[str, list[Relationship]] = {}
        for rel in relationships:
            if rel.relationship_type in _INBOUND_RELATIONSHIP_TYPES:
                reverse_adj.setdefault(rel.target_id, []).append(rel)

        # Reverse BFS from sinks to find all entities feeding into them
        visited: set[str] = set()
        queue = list(sink_ids)
        relevant_rels: list[Relationship] = []

        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            for rel in reverse_adj.get(current, []):
                relevant_rels.append(rel)
                if rel.source_id not in visited:
                    queue.append(rel.source_id)

        # Collect all entities found during traversal
        filtered_entities = [entity_map[eid] for eid in visited if eid in entity_map]

        # Build flow nodes (connections point forward, toward sinks)
        forward_lookup: dict[str, list[str]] = {}
        for rel in relevant_rels:
            forward_lookup.setdefault(rel.source_id, []).append(rel.target_id)

        flow_nodes: list[FlowNode] = []
        for entity in filtered_entities:
            connections = sorted(forward_lookup.get(entity.id, []))
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
            entities=canonical_sort_entities(filtered_entities),
            relationships=canonical_sort_relationships(relevant_rels),
            flow_nodes=flow_nodes,
            metadata={"perspective": self.perspective_name},
        )
