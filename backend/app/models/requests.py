from pydantic import BaseModel


class ScanRequest(BaseModel):
    repo_url: str
    branch: str = "main"
    perspectives: list[str] = ["manifest", "er", "dataflow"]


class TemplateCreateRequest(BaseModel):
    name: str
    perspective: str
    template_content: str
    placeholders: list[str]


class TemplateRenderRequest(BaseModel):
    template_id: str
    values: dict[str, str]
