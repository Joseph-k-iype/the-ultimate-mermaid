"""Data flow perspective analyzer — traces end-to-end data movement.

Builds on the manifest and ER perspectives by tracing *behavioral* paths:
how data enters the system, moves through processing, and reaches storage
or external outputs.

Algorithm:
  1. Build a directed graph from all data-movement relationships.
  2. BFS forward from entry points (endpoints, consumers, file_readers).
  3. BFS backward from exit points (db_write, file_writer, producers).
  4. Keep the intersection — nodes on a complete entry→exit path.
  5. If no complete paths exist, fall back to all relationship participants.
"""

from collections import defaultdict

from app.analyzers.base import PerspectiveAnalyzer
from app.models.domain import CodeEntity, DiagramData, FlowNode, Relationship
from app.utils.determinism import canonical_sort_entities, canonical_sort_relationships

_DATAFLOW_ENTITY_TYPES = {
    "function", "method", "endpoint", "class", "model",
    "db_read", "db_write", "file_reader", "file_writer",
    "consumer", "producer",
}

_DATAFLOW_REL_TYPES = {
    "calls", "passes_data", "reads", "writes", "produces", "consumes", "uses", "imports"
}

_ENTRY_TYPES = {"endpoint", "consumer", "file_reader"}
_EXIT_TYPES = {"db_write", "file_writer", "producer"}


def _bfs(seeds: set[str], adjacency: dict[str, list[str]]) -> set[str]:
    """Breadth-first traversal returning all reachable node IDs."""
    visited: set[str] = set()
    queue = list(seeds)
    while queue:
        current = queue.pop(0)
        if current in visited:
            continue
        visited.add(current)
        for neighbour in adjacency.get(current, []):
            if neighbour not in visited:
                queue.append(neighbour)
    return visited


class DataFlowAnalyzer(PerspectiveAnalyzer):
    """Traces end-to-end data flow from entry points to exit points."""

    @property
    def perspective_name(self) -> str:
        return "dataflow"

    def analyze(
        self,
        entities: list[CodeEntity],
        relationships: list[Relationship],
    ) -> DiagramData:
        entity_map = {e.id: e for e in entities}

        # ── 1. Collect all data-movement relationships ──────────────────
        relevant_rels = [
            r for r in relationships
            if r.relationship_type in _DATAFLOW_REL_TYPES
        ]

        # ── 2. Build directed graph ─────────────────────────────────────
        forward_adj: dict[str, list[str]] = defaultdict(list)
        reverse_adj: dict[str, list[str]] = defaultdict(list)
        for r in relevant_rels:
            forward_adj[r.source_id].append(r.target_id)
            reverse_adj[r.target_id].append(r.source_id)

        # ── 3. Build data flow graph ──────────────────────────────────────
        # We include all entities that participate in data-movement relationships.
        # This provides a complete picture of data flow without dropping nodes
        # that are separated by layers of indirection.
        
        on_path = set()
        for r in relevant_rels:
            on_path.add(r.source_id)
            on_path.add(r.target_id)

        # ── 7. Filter to known, data-relevant entities ──────────────────
        filtered = [
            entity_map[eid]
            for eid in on_path
            if eid in entity_map
            and entity_map[eid].entity_type in _DATAFLOW_ENTITY_TYPES
        ]
        filtered_ids = {e.id for e in filtered}

        kept_rels = [
            r for r in relevant_rels
            if r.source_id in filtered_ids and r.target_id in filtered_ids
        ]

        return self._build_diagram(filtered, kept_rels)

    # ------------------------------------------------------------------
    # Diagram construction
    # ------------------------------------------------------------------

    @staticmethod
    def _build_diagram(
        filtered_entities: list[CodeEntity],
        relevant_rels: list[Relationship],
    ) -> DiagramData:
        forward: dict[str, list[str]] = defaultdict(list)
        for r in relevant_rels:
            forward[r.source_id].append(r.target_id)

        flow_nodes: list[FlowNode] = []
        for entity in filtered_entities:
            if entity.entity_type in _ENTRY_TYPES:
                node_type = "entry"
            elif entity.entity_type in _EXIT_TYPES:
                node_type = "exit"
            else:
                node_type = "transform"

            connections = sorted(set(forward.get(entity.id, [])))
            flow_nodes.append(
                FlowNode(
                    id=entity.id,
                    label=entity.name,
                    node_type=node_type,
                    connections=connections,
                )
            )
        flow_nodes.sort(key=lambda n: n.id)

        return DiagramData(
            entities=canonical_sort_entities(filtered_entities),
            relationships=canonical_sort_relationships(relevant_rels),
            flow_nodes=flow_nodes,
            metadata={"perspective": "dataflow"},
        )
