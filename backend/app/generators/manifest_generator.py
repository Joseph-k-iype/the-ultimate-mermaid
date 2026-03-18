"""Mermaid generator for the data manifest perspective.

Produces a flowchart with component subgraphs containing entities
grouped by category (models, endpoints, stores, etc.).  No edges —
the manifest is a pure inventory showing *what data exists where*.
"""

from collections import defaultdict

from app.generators.base import MermaidGenerator
from app.models.domain import DiagramData

_CATEGORY_TYPES = {
    "Data Models": {"class", "model"},
    "Endpoints": {"endpoint"},
    "Data Stores": {"db_read", "db_write"},
    "File I/O": {"file_reader", "file_writer"},
    "Messaging": {"consumer", "producer"},
    "Processing": {"function", "method"},
}

# Mermaid shapes per category
_SHAPES = {
    "Data Models":  ("[", "]"),
    "Endpoints":    ("([", "])"),
    "Data Stores":  ("[(", ")]"),
    "File I/O":     ("{{", "}}"),
    "Messaging":    (">", "]"),
    "Processing":   ("[", "]"),
}


class ManifestMermaidGenerator(MermaidGenerator):
    """Generates a flowchart showing the data entity inventory."""

    @property
    def diagram_type(self) -> str:
        return "manifest"

    def generate(self, data: DiagramData) -> str:
        entities = data.entities
        entities, _, truncated = self.truncate_entities(entities, data.relationships)

        lines = ["flowchart TB"]
        if truncated:
            lines.append(f"    %% Showing top {len(entities)} entities")

        # Build component → category → entities mapping
        comp_cat: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
        for e in entities:
            comp = e.metadata.get("component", "ungrouped")
            cat = "Processing"
            for cat_name, type_set in _CATEGORY_TYPES.items():
                if e.entity_type in type_set:
                    cat = cat_name
                    break
            comp_cat[comp][cat].append(e)

        styles = []
        for comp in sorted(comp_cat.keys()):
            cats = comp_cat[comp]
            if comp != "ungrouped":
                safe_comp = self.sanitize_id(comp)
                lines.append(f'    subgraph comp_{safe_comp}["{comp}"]')
                styles.append(
                    f"    style comp_{safe_comp} fill:#fdfbf7,stroke:#d6d3d1,stroke-dasharray: 5 5"
                )

            for cat_name in ["Data Models", "Endpoints", "Data Stores",
                             "File I/O", "Messaging", "Processing"]:
                cat_entities = cats.get(cat_name, [])
                if not cat_entities:
                    continue

                safe_cat = self.sanitize_id(f"{comp}_{cat_name}")
                indent = "        " if comp != "ungrouped" else "    "
                lines.append(f'{indent}subgraph {safe_cat}["{cat_name}"]')

                shape_start, shape_end = _SHAPES.get(cat_name, ("[", "]"))
                for e in sorted(cat_entities, key=lambda x: x.name):
                    nid = self.sanitize_id(e.id)
                    label = self.sanitize_label(e.name)
                    # Enrich label with attributes for models
                    attrs = e.metadata.get("attributes", [])
                    if attrs:
                        short = attrs[:4]
                        label += "\\n" + "\\n".join(
                            self.sanitize_label(a) for a in short
                        )
                        if len(attrs) > 4:
                            label += f"\\n+{len(attrs) - 4} more"
                    lines.append(f"        {indent}{nid}{shape_start}{label}{shape_end}")

                lines.append(f"{indent}end")

            if comp != "ungrouped":
                lines.append("    end")

        # Styling
        lines.append("    classDef model fill:#faf5ff,stroke:#c084fc;")
        lines.append("    classDef endpoint fill:#eff6ff,stroke:#60a5fa;")
        lines.append("    classDef store fill:#fef08a,stroke:#ca8a04;")
        lines.append("    classDef fileio fill:#bbf7d0,stroke:#22c55e;")
        lines.append("    classDef msg fill:#fbcfe8,stroke:#db2777;")
        lines.append("    classDef proc fill:#ecfdf5,stroke:#6ee7b7;")

        for e in entities:
            nid = self.sanitize_id(e.id)
            if e.entity_type in {"class", "model"}:
                lines.append(f"    class {nid} model;")
            elif e.entity_type == "endpoint":
                lines.append(f"    class {nid} endpoint;")
            elif e.entity_type in {"db_read", "db_write"}:
                lines.append(f"    class {nid} store;")
            elif e.entity_type in {"file_reader", "file_writer"}:
                lines.append(f"    class {nid} fileio;")
            elif e.entity_type in {"consumer", "producer"}:
                lines.append(f"    class {nid} msg;")
            elif e.entity_type in {"function", "method"}:
                lines.append(f"    class {nid} proc;")

        lines.extend(styles)
        return "\n".join(lines)
