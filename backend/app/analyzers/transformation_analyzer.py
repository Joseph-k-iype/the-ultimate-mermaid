from app.analyzers.base import PerspectiveAnalyzer
from app.models.domain import CodeEntity, DiagramData, FlowNode, Relationship
from app.utils.determinism import canonical_sort_entities, canonical_sort_relationships

_SOURCE_TYPES = {"consumer", "file_reader", "db_read"}
_SINK_TYPES = {"producer", "file_writer", "db_write"}
_CHAIN_RELATIONSHIP_TYPES = {"calls", "uses", "produces", "consumes", "reads", "writes"}


class TransformationAnalyzer(PerspectiveAnalyzer):
    """Analyzes data transformation chains from consumers through function
    calls to producers/writers."""

    @property
    def perspective_name(self) -> str:
        return "transformation"

    def analyze(
        self,
        entities: list[CodeEntity],
        relationships: list[Relationship],
    ) -> DiagramData:
        entity_map = {e.id: e for e in entities}

        source_ids = {e.id for e in entities if e.entity_type in _SOURCE_TYPES}
        sink_ids = {e.id for e in entities if e.entity_type in _SINK_TYPES}

        # Build forward adjacency for chain-relevant relationships
        forward_adj: dict[str, list[Relationship]] = {}
        reverse_adj: dict[str, list[Relationship]] = {}
        for rel in relationships:
            if rel.relationship_type in _CHAIN_RELATIONSHIP_TYPES:
                forward_adj.setdefault(rel.source_id, []).append(rel)
                reverse_adj.setdefault(rel.target_id, []).append(rel)

        # Forward BFS from sources
        forward_reachable: set[str] = set()
        queue = list(source_ids)
        while queue:
            current = queue.pop(0)
            if current in forward_reachable:
                continue
            forward_reachable.add(current)
            for rel in forward_adj.get(current, []):
                if rel.target_id not in forward_reachable:
                    queue.append(rel.target_id)

        # Reverse BFS from sinks
        reverse_reachable: set[str] = set()
        queue = list(sink_ids)
        while queue:
            current = queue.pop(0)
            if current in reverse_reachable:
                continue
            reverse_reachable.add(current)
            for rel in reverse_adj.get(current, []):
                if rel.source_id not in reverse_reachable:
                    queue.append(rel.source_id)

        # Nodes on a transformation path are reachable from both directions
        on_path = forward_reachable & reverse_reachable

        # If no complete source-to-sink path exists, fall back to all
        # forward-reachable nodes from sources so the diagram is still useful
        if not on_path:
            on_path = forward_reachable

        # Collect entities and relationships on the transformation path
        filtered_entities = [entity_map[eid] for eid in on_path if eid in entity_map]

        relevant_rels = [
            rel
            for rel in relationships
            if rel.relationship_type in _CHAIN_RELATIONSHIP_TYPES
            and rel.source_id in on_path
            and rel.target_id in on_path
        ]

        # Build flow nodes
        flow_nodes: list[FlowNode] = []
        for entity in filtered_entities:
            connections = sorted(
                rel.target_id
                for rel in relevant_rels
                if rel.source_id == entity.id
            )
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
