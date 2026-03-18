from datetime import datetime

from pydantic import BaseModel, Field


class ScanResponse(BaseModel):
    scan_id: str
    status: str
    repo_url: str
    branch: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    perspectives: list[str] = Field(default_factory=list)
    components: list[str] = Field(default_factory=list)


class DiagramResponse(BaseModel):
    scan_id: str
    perspective: str
    mermaid_code: str
    metadata: dict = Field(default_factory=dict)


class TemplateResponse(BaseModel):
    id: str
    name: str
    perspective: str
    template_content: str
    placeholders: list[str]
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ErrorResponse(BaseModel):
    detail: str
    code: str
