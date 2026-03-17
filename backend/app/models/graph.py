"""Graph API response models."""

from pydantic import BaseModel, Field


class GraphNode(BaseModel):
    id: str
    label: str
    type: str
    properties: dict = Field(default_factory=dict)


class GraphEdge(BaseModel):
    source: str
    target: str
    type: str
    properties: dict = Field(default_factory=dict)


class KnowledgeGraphResponse(BaseModel):
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)
    stats: dict = Field(default_factory=dict)


class ConceptNode(BaseModel):
    id: str
    label: str
    broader: str | None = None
    narrower: list[str] = Field(default_factory=list)


class ConceptHierarchyResponse(BaseModel):
    concepts: list[ConceptNode]


class GraphStatusResponse(BaseModel):
    available: bool
    node_count: int = 0
    edge_count: int = 0
    details: dict = Field(default_factory=dict)
