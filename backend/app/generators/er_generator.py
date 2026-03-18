from collections import defaultdict

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
    """Generates Mermaid classDiagram syntax for entity-relationship diagrams (supports namespaces for component grouping)."""

    @property
    def diagram_type(self) -> str:
        return "class"

    def generate(self, data: DiagramData) -> str:
        lines: list[str] = ["classDiagram"]

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

        # Group by component and emit entity blocks within namespaces
        component_groups: dict[str, list[CodeEntity]] = defaultdict(list)
        for entity in sorted(entities, key=lambda e: e.name):
            comp = entity.metadata.get("component", "ungrouped")
            component_groups[comp].append(entity)

        # Draw namespace subgraphs for components
        for comp in sorted(component_groups.keys()):
            group = component_groups[comp]
            if comp != "ungrouped":
                safe_comp = self.sanitize_id(comp)
                lines.append(f"    namespace {safe_comp} {{")
                for entity in group:
                    lines.extend(self._render_entity(entity, indent="      "))
                lines.append("    }")
            else:
                for entity in group:
                    lines.extend(self._render_entity(entity, indent="    "))

        lines.append("")

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

    def _render_entity(self, entity: CodeEntity, indent: str = "    ") -> list[str]:
        """Render a single class block with its attributes/methods."""
        lines: list[str] = []
        safe_name = self.sanitize_id(entity.name)
        attributes: list[str] = entity.metadata.get("attributes", [])
        methods: list[str] = entity.metadata.get("methods", [])

        if not attributes and not methods:
            # Emit an empty class
            lines.append(f"{indent}class {safe_name}")
            return lines

        lines.append(f"{indent}class {safe_name} {{")
        for attr in sorted(attributes):
            safe_attr = self.sanitize_id(attr.replace(":", " "))
            lines.append(f"{indent}    {safe_attr}")
        for method in sorted(methods):
            safe_method = self.sanitize_id(method)
            lines.append(f"{indent}    {safe_method}()")
        lines.append(f"{indent}}}")
        return lines

    @staticmethod
    def _render_relationship(
        src: CodeEntity, tgt: CodeEntity, rel: Relationship
    ) -> str:
        """Render a single class diagram relationship line."""
        src_name = MermaidGenerator.sanitize_id(src.name)
        tgt_name = MermaidGenerator.sanitize_id(tgt.name)
        
        # Determine arrow type based on relationship semantic
        if rel.relationship_type == "inherits":
            arrow = "<|--"
        elif rel.relationship_type == "contains":
            arrow = "*--"
        else:
            arrow = "-->"
            
        label = _RELATIONSHIP_LABELS.get(rel.relationship_type, rel.relationship_type)
        return f'    {tgt_name} {arrow} {src_name} : "{label}"'
