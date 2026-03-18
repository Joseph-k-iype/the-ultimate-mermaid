"""Mermaid generator for the data flow perspective.

Produces a left-to-right flowchart showing end-to-end data movement
grouped by component.  Edges are labeled with the relationship type
(calls, reads, writes, produces, consumes, passes_data) so the reader
can see *what kind* of data movement each connection represents.
"""

from app.generators.base import MermaidGenerator
from app.models.domain import DiagramData

# Edge styles per relationship type.
_EDGE_STYLE = {
    "calls":       ("-->",  "calls"),
    "passes_data": ("-.->", "data"),
    "reads":       ("-->",  "reads"),
    "writes":      ("-->",  "writes"),
    "produces":    ("-.->", "produces"),
    "consumes":    ("-.->", "consumes"),
}

# Node shapes per entity type.
_SHAPES = {
    "endpoint":    ("([", "])"),      # stadium — entry
    "consumer":    ("([", "])"),      # stadium — entry
    "file_reader": ("([", "])"),      # stadium — entry
    "db_read":     ("[(", ")]"),      # cylinder — store
    "db_write":    ("[(", ")]"),      # cylinder — store
    "file_writer": ("{{", "}}"),      # hexagon — file
    "producer":    ("[[", "]]"),      # subroutine — messaging exit
    "class":       ("[", "]"),
    "model":       ("[", "]"),
    "function":    ("[", "]"),
    "method":      ("[", "]"),
}


class DataFlowMermaidGenerator(MermaidGenerator):
    """Generates a flowchart visualizing end-to-end data flow."""

    @property
    def diagram_type(self) -> str:
        return "dataflow"

    def generate(self, data: DiagramData) -> str:
        entities = data.entities
        relationships = data.relationships

        entities, relationships, truncated = self.truncate_entities(
            entities, relationships
        )

        lines = ["flowchart LR"]
        if truncated:
            lines.append(
                f"    %% Showing top {len(entities)} most-connected nodes"
            )

        # ── Build labeled edges ─────────────────────────────────────────
        edges: list[str] = []
        seen: set[str] = set()
        for r in relationships:
            arrow, label = _EDGE_STYLE.get(
                r.relationship_type, ("-->", r.relationship_type)
            )
            src = self.sanitize_id(r.source_id)
            tgt = self.sanitize_id(r.target_id)
            key = f"{src}-{label}-{tgt}"
            if key not in seen:
                seen.add(key)
                edges.append(f"{src} {arrow}|{label}| {tgt}")

        # ── Group entities by component ─────────────────────────────────
        components = self.group_by_component(entities)
        subgraph_styles: list[str] = []

        for comp_name in sorted(components.keys()):
            comp_entities = components[comp_name]
            in_subgraph = comp_name != "ungrouped"

            if in_subgraph:
                safe = self.sanitize_id(comp_name)
                lines.append(f'    subgraph component_{safe}["{comp_name}"]')
                subgraph_styles.append(
                    f"    style component_{safe} "
                    f"fill:#fdfbf7,stroke:#d6d3d1,stroke-dasharray: 5 5"
                )

            indent = "        " if in_subgraph else "    "
            for entity in sorted(comp_entities, key=lambda e: e.name):
                nid = self.sanitize_id(entity.id)
                label = self.sanitize_label(entity.name)
                s, e = _SHAPES.get(entity.entity_type, ("[", "]"))
                lines.append(f"{indent}{nid}{s}{label}{e}")

            if in_subgraph:
                lines.append("    end")

        # ── Edges (after nodes so Mermaid resolves IDs) ─────────────────
        for edge in edges:
            lines.append(f"    {edge}")

        # ── Subgraph styles ─────────────────────────────────────────────
        lines.extend(subgraph_styles)

        # ── Node class definitions ──────────────────────────────────────
        lines.append("    classDef entry fill:#bfdbfe,stroke:#2563eb;")
        lines.append("    classDef store fill:#fef08a,stroke:#ca8a04;")
        lines.append("    classDef fileio fill:#bbf7d0,stroke:#22c55e;")
        lines.append("    classDef msg fill:#fbcfe8,stroke:#db2777;")
        lines.append("    classDef transform fill:#f5f5f4,stroke:#a8a29e;")

        for entity in entities:
            nid = self.sanitize_id(entity.id)
            if entity.entity_type in {"endpoint", "consumer", "file_reader"}:
                lines.append(f"    class {nid} entry;")
            elif entity.entity_type in {"db_read", "db_write", "model"}:
                lines.append(f"    class {nid} store;")
            elif entity.entity_type in {"file_writer"}:
                lines.append(f"    class {nid} fileio;")
            elif entity.entity_type in {"producer"}:
                lines.append(f"    class {nid} msg;")
            else:
                lines.append(f"    class {nid} transform;")

        return "\n".join(lines)
