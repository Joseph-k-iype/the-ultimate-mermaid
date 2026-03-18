from collections import defaultdict

from app.generators.base import MermaidGenerator
from app.models.domain import DiagramData, CodeEntity, Relationship, FlowNode


# Entity types considered output sinks (databases)
_SINK_TYPES = {"db_write", "db_read"}
# Entity types considered file outputs
_FILE_TYPES = {"file_writer"}


class OutputMermaidGenerator(MermaidGenerator):
    """Generates Mermaid flowchart TD diagrams for output/sink visualization."""

    @property
    def diagram_type(self) -> str:
        return "output"

    def generate(self, data: DiagramData) -> str:
        lines: list[str] = ["flowchart TD"]

        if data.flow_nodes:
            lines.extend(self._generate_from_flow_nodes(data.flow_nodes))
        elif data.entities or data.relationships:
            lines.extend(self._generate_from_entities(data.entities, data.relationships))
        else:
            lines.append("    %% No data available")
            lines.append('    empty["No output data"]')

        return "\n".join(lines)

    def _generate_from_flow_nodes(self, flow_nodes: list[FlowNode]) -> list[str]:
        lines: list[str] = []

        # Group nodes by type for subgraphs
        groups: dict[str, list[FlowNode]] = defaultdict(list)
        for node in sorted(flow_nodes, key=lambda n: n.id):
            groups[node.node_type].append(node)

        for node_type in sorted(groups.keys()):
            subgraph_label = self.sanitize_label(node_type)
            subgraph_id = self.sanitize_id(node_type)
            lines.append(f"    subgraph {subgraph_id} [{subgraph_label}]")
            for node in groups[node_type]:
                lines.append(self._render_flow_node(node))
            lines.append("    end")

        # Emit edges
        for node in sorted(flow_nodes, key=lambda n: n.id):
            sid = self.sanitize_id(node.id)
            for conn in sorted(node.connections):
                tid = self.sanitize_id(conn)
                lines.append(f"    {sid} --> {tid}")

        return lines

    def _render_flow_node(self, node: FlowNode) -> str:
        sid = self.sanitize_id(node.id)
        label = self.sanitize_label(node.label)

        if node.node_type == "sink":
            return f'        {sid}[("{label}")]'
        elif node.node_type == "file":
            return f'        {sid}>"{label}"]'
        else:
            return f'        {sid}["{label}"]'

    def _generate_from_entities(
        self, entities: list[CodeEntity], relationships: list[Relationship]
    ) -> list[str]:
        lines: list[str] = []

        # Truncate if too many entities
        entities, relationships, truncated = self.truncate_entities(
            entities, relationships
        )
        if truncated:
            lines.append(f"    %% Showing top {len(entities)} most-connected entities")

        entity_map: dict[str, CodeEntity] = {e.id: e for e in entities}

        # Group entities by component (fall back to entity_type)
        groups: dict[str, list[CodeEntity]] = defaultdict(list)
        for entity in sorted(entities, key=lambda e: (e.metadata.get("component", e.entity_type), e.name)):
            key = entity.metadata.get("component", entity.entity_type)
            groups[key].append(entity)

        for etype in sorted(groups.keys()):
            subgraph_id = self.sanitize_id(etype)
            subgraph_label = self.sanitize_label(etype)
            lines.append(f"    subgraph {subgraph_id} [{subgraph_label}]")
            for entity in groups[etype]:
                sid = self.sanitize_id(entity.id)
                label = self.sanitize_label(entity.name)
                if entity.entity_type in _SINK_TYPES:
                    lines.append(f'        {sid}[("{label}")]')
                elif entity.entity_type in _FILE_TYPES:
                    lines.append(f'        {sid}[\\"{label}"/]')
                else:
                    lines.append(f'        {sid}["{label}"]')
            lines.append("    end")

        entity_ids = {e.id for e in entities}
        for rel in sorted(relationships, key=lambda r: (r.source_id, r.target_id)):
            if rel.source_id in entity_ids and rel.target_id in entity_ids:
                src = self.sanitize_id(rel.source_id)
                tgt = self.sanitize_id(rel.target_id)
                lines.append(f"    {src} --> {tgt}")

        return lines
