import re
from abc import ABC, abstractmethod
from collections import Counter, defaultdict

from app.models.domain import CodeEntity, DiagramData, Relationship


# Maximum entities to include in a single Mermaid diagram.
# Beyond this, Mermaid's browser renderer hits text-size or parse limits.
MAX_ENTITIES = 2000


class MermaidGenerator(ABC):
    """Abstract base class for Mermaid diagram generators."""

    @property
    @abstractmethod
    def diagram_type(self) -> str:
        """Return the type identifier for this generator."""

    @abstractmethod
    def generate(self, data: DiagramData) -> str:
        """Generate a Mermaid syntax string from DiagramData."""

    # Mermaid reserved keywords that cannot be used as node IDs
    _RESERVED = frozenset({
        "end", "graph", "subgraph", "flowchart", "sequenceDiagram",
        "classDiagram", "erDiagram", "style", "click", "class",
        "default", "linkStyle", "direction", "participant",
    })

    @staticmethod
    def sanitize_id(raw_id: str) -> str:
        """Make an ID safe for use in Mermaid diagrams.

        Replaces ::, /, ., spaces, hyphens, and other special chars
        with underscores. Ensures ID starts with a letter. Prefixes
        reserved keywords.
        """
        sanitized = re.sub(r"[:]{2}|[/.\s\-@#$%^&*()+=\[\]{}<>,;:!?~`|'\"\\]", "_", raw_id)
        sanitized = sanitized.lstrip("_")
        # Ensure it starts with a letter (Mermaid requires this)
        if sanitized and not sanitized[0].isalpha():
            sanitized = "n_" + sanitized
        # Avoid reserved keywords
        if sanitized.lower() in MermaidGenerator._RESERVED:
            sanitized = "n_" + sanitized
        # Ensure non-empty
        if not sanitized:
            sanitized = "n_empty"
        return sanitized

    @staticmethod
    def sanitize_label(label: str) -> str:
        """Escape characters that break Mermaid label parsing."""
        result = label.replace('"', "#quot;")
        result = result.replace("(", "#40;").replace(")", "#41;")
        result = result.replace("[", "#91;").replace("]", "#93;")
        result = result.replace("{", "#123;").replace("}", "#125;")
        return result

    @staticmethod
    def truncate_entities(
        entities: list[CodeEntity],
        relationships: list[Relationship],
        max_entities: int = MAX_ENTITIES,
    ) -> tuple[list[CodeEntity], list[Relationship], bool]:
        """Keep the most-connected entities up to *max_entities*.

        Returns (entities, relationships, was_truncated).
        """
        if len(entities) <= max_entities:
            return entities, relationships, False

        # Rank by relationship density (most connected first)
        counts: Counter[str] = Counter()
        for rel in relationships:
            counts[rel.source_id] += 1
            counts[rel.target_id] += 1

        # Sort: most connected first, then alphabetical for determinism
        ranked = sorted(
            entities,
            key=lambda e: (-counts.get(e.id, 0), e.name),
        )
        kept = ranked[:max_entities]
        kept_ids = {e.id for e in kept}

        kept_rels = [
            r for r in relationships
            if r.source_id in kept_ids and r.target_id in kept_ids
        ]
        return kept, kept_rels, True

    @staticmethod
    def group_by_component(entities: list[CodeEntity]) -> dict[str, list[CodeEntity]]:
        """Group entities by their component metadata."""
        groups: dict[str, list[CodeEntity]] = defaultdict(list)
        for e in entities:
            groups[e.metadata.get("component", "ungrouped")].append(e)
        return groups


def filter_diagram_data(dd: DiagramData, entity_ids: set[str]) -> DiagramData:
    """Return a copy of DiagramData filtered to only the given entity IDs."""
    filtered_entities = [e for e in dd.entities if e.id in entity_ids]
    filtered_ids = {e.id for e in filtered_entities}
    filtered_rels = [
        r for r in dd.relationships
        if r.source_id in filtered_ids and r.target_id in filtered_ids
    ]
    return DiagramData(
        entities=filtered_entities,
        relationships=filtered_rels,
        flow_nodes=[n for n in (dd.flow_nodes or []) if n.id in filtered_ids],
        metadata=dd.metadata,
    )

