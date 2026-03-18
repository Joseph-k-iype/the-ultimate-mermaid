from collections import defaultdict
from typing import Any

from app.generators.base import MermaidGenerator
from app.models.domain import CodeEntity


class CICDMermaidGenerator(MermaidGenerator):
    """Generates a flowchart for CI/CD pipelines showing stages and jobs."""

    @property
    def diagram_type(self) -> str:
        return "cicd"

    def generate(self, data: Any) -> str:
        entities = data.entities
        relationships = data.relationships

        # Truncate if too large to prevent rendering issues
        entities, relationships, truncated = self.truncate_entities(entities, relationships)
        if truncated:
            truncation_notice = f"%% Showing top {len(entities)} most-connected pipeline components out of {len(data.entities)}\n"
        else:
            truncation_notice = ""

        # Unpack relationships
        edges = []
        for r in relationships:
            edges.append(f"{self.sanitize_id(r.source_id)} --> {self.sanitize_id(r.target_id)}")

        # Group by component
        components: dict[str, list[CodeEntity]] = defaultdict(list)
        for entity in entities:
            comp = entity.metadata.get("component") if getattr(entity, "metadata", None) else None
            if comp:
                components[comp].append(entity)
            else:
                components["root"].append(entity)

        lines = ["flowchart LR"]
        if truncation_notice:
            lines.append(truncation_notice)

        # Draw nodes optionally grouped by component subgraph
        styles = []
        for comp_name, comp_entities in components.items():
            if comp_name != "root":
                safe_comp = self.sanitize_id(comp_name)
                lines.append(f"    subgraph component_{safe_comp}[\"{comp_name}\"]")
                styles.append(f"    style component_{safe_comp} fill:#f9f9f9,stroke:#e5e7eb,stroke-dasharray: 5 5")
                indent = "        "
            else:
                indent = "    "

            for entity in comp_entities:
                node_id = self.sanitize_id(entity.id)
                label = self.sanitize_label(entity.name)

                if entity.entity_type == "pipeline_trigger":
                    shape_start, shape_end = "([", "])"
                elif entity.entity_type == "pipeline_stage":
                    shape_start, shape_end = "[[", "]]"
                else:
                    shape_start, shape_end = "[", "]"

                lines.append(f"{indent}{node_id}{shape_start}{label}{shape_end}")

            if comp_name != "root":
                lines.append("    end")

        lines.extend([f"    {e}" for e in edges])

        # Styling
        lines.append("    classDef trigger fill:#dbeafe,stroke:#3b82f6;")
        lines.append("    classDef stage fill:#fdf4ff,stroke:#d946ef;")
        lines.append("    classDef job fill:#f3f4f6,stroke:#9ca3af;")

        for e in entities:
            nid = self.sanitize_id(e.id)
            if e.entity_type == "pipeline_trigger":
                lines.append(f"    class {nid} trigger;")
            elif e.entity_type == "pipeline_stage":
                lines.append(f"    class {nid} stage;")
            elif e.entity_type == "pipeline_job":
                lines.append(f"    class {nid} job;")

        return "\n".join(lines)
