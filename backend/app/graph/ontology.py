"""W3C SKOS + RDFS ontology for PatternViz code entities and relationships."""

from dataclasses import dataclass, field
from enum import Enum


class EntityClass(str, Enum):
    """SKOS concept hierarchy for entity types."""

    # Broader concepts
    CODE_CONSTRUCT = "CodeConstruct"
    API_ELEMENT = "APIElement"
    DATA_ACCESSOR = "DataAccessor"
    MESSAGE_HANDLER = "MessageHandler"

    # Narrower: CodeConstruct
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
    VARIABLE = "variable"

    # Narrower: APIElement
    ENDPOINT = "endpoint"
    MODEL = "model"

    # Narrower: DataAccessor
    DB_READ = "db_read"
    DB_WRITE = "db_write"
    FILE_READER = "file_reader"
    FILE_WRITER = "file_writer"

    # Narrower: MessageHandler
    CONSUMER = "consumer"
    PRODUCER = "producer"


class OntologyRelationType(str, Enum):
    """All domain relationship types plus semantic ones."""

    # Code relationships
    CALLS = "calls"
    INHERITS = "inherits"
    IMPORTS = "imports"
    USES = "uses"
    CONTAINS = "contains"
    PRODUCES = "produces"
    CONSUMES = "consumes"
    READS = "reads"
    WRITES = "writes"

    # SKOS semantic relationships
    BROADER = "broader"
    NARROWER = "narrower"
    RELATED = "related"

    # Metadata relationships
    HAS_TAG = "has_tag"
    BELONGS_TO_SCAN = "belongs_to_scan"
    LINKED_TO_PATTERN = "linked_to_pattern"


CONCEPT_HIERARCHY: dict[str, list[str]] = {
    "CodeConstruct": ["class", "function", "method", "variable"],
    "APIElement": ["endpoint", "model"],
    "DataAccessor": ["db_read", "db_write", "file_reader", "file_writer"],
    "MessageHandler": ["consumer", "producer"],
}

# Reverse lookup: entity_type -> broader concept
ENTITY_TO_CONCEPT: dict[str, str] = {}
for _broader, _narrower_list in CONCEPT_HIERARCHY.items():
    for _entity_type in _narrower_list:
        ENTITY_TO_CONCEPT[_entity_type] = _broader

# All leaf entity type strings (the ones used in CodeEntity.entity_type)
ALL_ENTITY_TYPES: set[str] = set(ENTITY_TO_CONCEPT.keys())

# Code-only relationship types (excluding semantic/metadata)
CODE_RELATIONSHIP_TYPES: set[str] = {
    "calls", "inherits", "imports", "uses", "contains",
    "produces", "consumes", "reads", "writes",
}


@dataclass
class PerspectiveDefinition:
    """Declares which entity_types and relationship_types a perspective selects.

    Replaces hard-coded filtering in each perspective analyzer.
    """

    name: str
    entity_types: list[str]
    relationship_types: list[str]
    description: str = ""


PERSPECTIVE_DEFINITIONS: dict[str, PerspectiveDefinition] = {
    "er": PerspectiveDefinition(
        name="er",
        entity_types=["class", "model"],
        relationship_types=["inherits", "contains", "uses"],
        description="Entity-Relationship: classes, models and their structural relationships",
    ),
    "ingestion": PerspectiveDefinition(
        name="ingestion",
        entity_types=["endpoint", "consumer", "file_reader"],
        relationship_types=["calls", "uses", "reads", "consumes"],
        description="Data ingestion: entry points and data consumers",
    ),
    "transformation": PerspectiveDefinition(
        name="transformation",
        entity_types=[
            "consumer", "file_reader", "db_read",
            "producer", "file_writer", "db_write", "function",
        ],
        relationship_types=["calls", "uses", "produces", "consumes", "reads", "writes"],
        description="Data transformation: processing between ingestion and output",
    ),
    "output": PerspectiveDefinition(
        name="output",
        entity_types=["producer", "file_writer", "db_write"],
        relationship_types=["calls", "uses", "writes", "produces"],
        description="Output/export: data sinks and producers",
    ),
}

# Cypher statements for graph schema initialization
SCHEMA_CYPHER: list[str] = [
    # Indexes
    "CREATE INDEX IF NOT EXISTS FOR (e:CodeEntity) ON (e.id)",
    "CREATE INDEX IF NOT EXISTS FOR (s:Scan) ON (s.id)",
    "CREATE INDEX IF NOT EXISTS FOR (p:Pattern) ON (p.id)",
    "CREATE INDEX IF NOT EXISTS FOR (c:Concept) ON (c.name)",
    # Note: FalkorDB uses slightly different syntax; these are adjusted at runtime
]
