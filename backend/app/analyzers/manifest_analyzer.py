"""Data manifest perspective analyzer — catalogs all data entities grouped by component."""

from collections import defaultdict

from app.analyzers.base import PerspectiveAnalyzer
from app.models.domain import CodeEntity, DiagramData, FlowNode, Relationship
from app.utils.determinism import canonical_sort_entities, canonical_sort_relationships

# Every entity type that represents data or participates in data handling.
_MANIFEST_ENTITY_TYPES = {
    "class", "model",                       # Data structures
    "endpoint",                             # Data entry points (API)
    "function", "method",                   # Data processors
    "db_read", "db_write",                  # Database operations
    "file_reader", "file_writer",           # File I/O
    "consumer", "producer",                 # Messaging
}

# Logical categories for grouping within a component.
CATEGORY_ORDER = [
    ("Data Models", {"class", "model"}),
    ("Endpoints", {"endpoint"}),
    ("Data Stores", {"db_read", "db_write"}),
    ("File I/O", {"file_reader", "file_writer"}),
    ("Messaging", {"consumer", "producer"}),
    ("Processing", {"function", "method"}),
]


class ManifestAnalyzer(PerspectiveAnalyzer):
    """Produces a complete catalog of all data-relevant entities."""

    @property
    def perspective_name(self) -> str:
        return "manifest"

    def analyze(
        self,
        entities: list[CodeEntity],
        relationships: list[Relationship],
    ) -> DiagramData:
        manifest_entities = [
            e for e in entities if e.entity_type in _MANIFEST_ENTITY_TYPES
        ]
        manifest_ids = {e.id for e in manifest_entities}

        # Keep relationships where both endpoints are in the manifest.
        manifest_rels = [
            r for r in relationships
            if r.source_id in manifest_ids and r.target_id in manifest_ids
        ]

        # Build flow nodes — one per entity, tagged with category.
        flow_nodes: list[FlowNode] = []
        for entity in manifest_entities:
            category = "Processing"
            for cat_name, type_set in CATEGORY_ORDER:
                if entity.entity_type in type_set:
                    category = cat_name
                    break

            flow_nodes.append(
                FlowNode(
                    id=entity.id,
                    label=entity.name,
                    node_type=category,
                    connections=[],
                )
            )
        flow_nodes.sort(key=lambda n: n.id)

        # Build component→category→entities index for metadata.
        comp_index: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for e in manifest_entities:
            comp = e.metadata.get("component", "ungrouped")
            for cat_name, type_set in CATEGORY_ORDER:
                if e.entity_type in type_set:
                    comp_index[comp][cat_name] += 1
                    break

        return DiagramData(
            entities=canonical_sort_entities(manifest_entities),
            relationships=canonical_sort_relationships(manifest_rels),
            flow_nodes=flow_nodes,
            metadata={
                "perspective": self.perspective_name,
                "summary": {comp: dict(cats) for comp, cats in comp_index.items()},
            },
        )
