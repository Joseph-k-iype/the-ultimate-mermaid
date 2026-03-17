import re
from abc import ABC, abstractmethod
from collections import Counter

from app.models.domain import CodeEntity, DiagramData, Relationship


# Maximum entities to include in a single Mermaid diagram.
# Beyond this, Mermaid's browser renderer hits text-size or parse limits.
MAX_ENTITIES = 80


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

