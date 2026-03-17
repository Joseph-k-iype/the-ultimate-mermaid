from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class PatternStatus(str, Enum):
    draft = "draft"
    review = "review"
    approved = "approved"
    deprecated = "deprecated"


class PatternModel(BaseModel):
    id: str
    title: str
    description: str
    owner: str
    status: PatternStatus = PatternStatus.draft
    tags: list[str] = Field(default_factory=list)
    content: str = ""
    mermaid_diagrams: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    version: int = 1
    linked_scan_id: str | None = None


class PatternCreateRequest(BaseModel):
    title: str
    description: str
    owner: str
    tags: list[str] = Field(default_factory=list)
    content: str = ""
    linked_scan_id: str | None = None


class PatternUpdateRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    owner: str | None = None
    tags: list[str] | None = None
    content: str | None = None


class PatternSearchParams(BaseModel):
    query: str | None = None
    tags: list[str] | None = None
    status: PatternStatus | None = None
    owner: str | None = None


class PatternResponse(BaseModel):
    id: str
    title: str
    description: str
    owner: str
    status: PatternStatus
    tags: list[str]
    content: str
    mermaid_diagrams: list[str]
    created_at: datetime
    updated_at: datetime
    version: int
    linked_scan_id: str | None = None


class PatternListItem(BaseModel):
    id: str
    title: str
    description: str
    owner: str
    status: PatternStatus
    tags: list[str]
    updated_at: datetime
    version: int


class PatternSearchResponse(BaseModel):
    results: list[PatternListItem]
    total: int
