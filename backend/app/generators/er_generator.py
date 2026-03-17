from app.generators.base import MermaidGenerator
from app.models.domain import DiagramData, CodeEntity, Relationship


_RELATIONSHIP_LABELS: dict[str, str] = {
    "inherits": "inherits",
    "contains": "contains",
    "uses": "uses",
    "calls": "calls",
    "imports": "imports",
    "produces": "produces",
    "consumes": "consumes",
    "reads": "reads",
    "writes": "writes",
}


class ERMermaidGenerator(MermaidGenerator):
    """Generates Mermaid erDiagram syntax for entity-relationship diagrams."""

    @property
    def diagram_type(self) -> str:
        return "er"

    def generate(self, data: DiagramData) -> str:
        lines: list[str] = ["erDiagram"]

        if not data.entities and not data.relationships:
            lines.append("    %% No data available")
            return "\n".join(lines)

        entities = data.entities
        relationships = data.relationships

        # Truncate if too many entities
        entities, relationships, truncated = self.truncate_entities(
            entities, relationships
        )
        if truncated:
            lines.append(f"    %% Showing top {len(entities)} most-connected entities")

        entity_map: dict[str, CodeEntity] = {e.id: e for e in entities}

        # Emit entity blocks sorted by name
        for entity in sorted(entities, key=lambda e: e.name):
            lines.extend(self._render_entity(entity))

        # Emit relationships sorted deterministically
        for rel in sorted(
            relationships, key=lambda r: (r.source_id, r.target_id, r.relationship_type)
        ):
            src = entity_map.get(rel.source_id)
            tgt = entity_map.get(rel.target_id)
            if src is None or tgt is None:
                continue
            lines.append(self._render_relationship(src, tgt, rel))

        return "\n".join(lines)

    def _render_entity(self, entity: CodeEntity) -> list[str]:
        """Render a single entity block with its attributes/methods."""
        lines: list[str] = []
        safe_name = self.sanitize_id(entity.name)
        attributes: list[str] = entity.metadata.get("attributes", [])
        methods: list[str] = entity.metadata.get("methods", [])

        if not attributes and not methods:
            # Emit an empty entity so it still appears in the diagram
            lines.append(f"    {safe_name} {{")
            lines.append("    }")
            return lines

        lines.append(f"    {safe_name} {{")
        for attr in sorted(attributes):
            safe_attr = self.sanitize_id(attr)
            lines.append(f"        string {safe_attr}")
        for method in sorted(methods):
            safe_method = self.sanitize_id(method)
            lines.append(f"        method {safe_method}")
        lines.append("    }")
        return lines

    @staticmethod
    def _render_relationship(
        src: CodeEntity, tgt: CodeEntity, rel: Relationship
    ) -> str:
        """Render a single ER relationship line."""
        src_name = MermaidGenerator.sanitize_id(src.name)
        tgt_name = MermaidGenerator.sanitize_id(tgt.name)
        label = _RELATIONSHIP_LABELS.get(rel.relationship_type, rel.relationship_type)
        return f'    {src_name} ||--o{{ {tgt_name} : "{label}"'
