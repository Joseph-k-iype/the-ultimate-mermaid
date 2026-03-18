from collections import defaultdict

from app.generators.base import MermaidGenerator
from app.models.domain import DiagramData, CodeEntity, Relationship, FlowNode


class IngestionMermaidGenerator(MermaidGenerator):
    """Generates Mermaid flowchart TD diagrams for data ingestion flows."""

    @property
    def diagram_type(self) -> str:
        return "ingestion"

    def generate(self, data: DiagramData) -> str:
        lines: list[str] = ["flowchart TD"]

        if data.flow_nodes:
            lines.extend(self._generate_from_flow_nodes(data.flow_nodes))
        elif data.entities or data.relationships:
            lines.extend(self._generate_from_entities(data.entities, data.relationships))
        else:
            lines.append("    %% No data available")
            lines.append('    empty["No ingestion data"]')

        return "\n".join(lines)

    def _generate_from_flow_nodes(self, flow_nodes: list[FlowNode]) -> list[str]:
        lines: list[str] = []
        sorted_nodes = sorted(flow_nodes, key=lambda n: n.id)

        for node in sorted_nodes:
            sid = self.sanitize_id(node.id)
            label = self.sanitize_label(node.label)
            if node.node_type == "entry":
                lines.append(f'    {sid}(["{label}"])')
            else:
                lines.append(f'    {sid}["{label}"]')

        for node in sorted_nodes:
            sid = self.sanitize_id(node.id)
            for conn in sorted(node.connections):
                tid = self.sanitize_id(conn)
                lines.append(f"    {sid} --> {tid}")

        return lines

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

        # Group entities by component (fall back to file_path)
        groups: dict[str, list[CodeEntity]] = defaultdict(list)
        for entity in sorted(entities, key=lambda e: (e.metadata.get("component", e.file_path), e.name)):
            key = entity.metadata.get("component", entity.file_path)
            groups[key].append(entity)

        entity_ids = {e.id for e in entities}

        for file_path in sorted(groups.keys()):
            subgraph_id = self.sanitize_id(file_path)
            lines.append(f"    subgraph {subgraph_id} [{self.sanitize_label(file_path)}]")
            for entity in groups[file_path]:
                sid = self.sanitize_id(entity.id)
                label = self.sanitize_label(entity.name)
                entry_types = {"consumer", "endpoint", "file_reader", "db_read"}
                if entity.entity_type in entry_types:
                    lines.append(f'        {sid}(["{label}"])')
                else:
                    lines.append(f'        {sid}["{label}"]')
            lines.append("    end")

        for rel in sorted(relationships, key=lambda r: (r.source_id, r.target_id)):
            if rel.source_id in entity_ids and rel.target_id in entity_ids:
                src = self.sanitize_id(rel.source_id)
                tgt = self.sanitize_id(rel.target_id)
                lines.append(f"    {src} --> {tgt}")

        return lines
