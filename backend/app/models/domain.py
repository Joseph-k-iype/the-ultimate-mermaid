from typing import Literal

from pydantic import BaseModel, Field


class CodeEntity(BaseModel):
    id: str
    name: str
    entity_type: Literal[
        "class",
        "function",
        "method",
        "variable",
        "endpoint",
        "model",
        "consumer",
        "producer",
        "file_reader",
        "file_writer",
        "db_read",
        "db_write",
    ]
    file_path: str
    line_number: int
    metadata: dict = Field(default_factory=dict)


class Relationship(BaseModel):
    source_id: str
    target_id: str
    relationship_type: Literal[
        "inherits",
        "contains",
        "calls",
        "imports",
        "uses",
        "produces",
        "consumes",
        "reads",
        "writes",
    ]
    metadata: dict = Field(default_factory=dict)


class FlowNode(BaseModel):
    id: str
    label: str
    node_type: str
    connections: list[str] = Field(default_factory=list)


class DiagramData(BaseModel):
    entities: list[CodeEntity] = Field(default_factory=list)
    relationships: list[Relationship] = Field(default_factory=list)
    flow_nodes: list[FlowNode] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)
