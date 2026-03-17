import uuid
from datetime import datetime, timezone

from jinja2 import Template

from app.models.requests import TemplateCreateRequest
from app.models.responses import TemplateResponse


class TemplateService:
    """In-memory template storage and rendering."""

    def __init__(self) -> None:
        self._templates: dict[str, TemplateResponse] = {}

    def create_template(self, req: TemplateCreateRequest) -> TemplateResponse:
        template_id = uuid.uuid4().hex
        resp = TemplateResponse(
            id=template_id,
            name=req.name,
            perspective=req.perspective,
            template_content=req.template_content,
            placeholders=req.placeholders,
            created_at=datetime.now(timezone.utc),
        )
        self._templates[template_id] = resp
        return resp

    def get_template(self, template_id: str) -> TemplateResponse | None:
        return self._templates.get(template_id)

    def list_templates(self) -> list[TemplateResponse]:
        return list(self._templates.values())

    def render_template(self, template_id: str, values: dict[str, str]) -> str | None:
        tmpl = self._templates.get(template_id)
        if tmpl is None:
            return None
        jinja_tmpl = Template(tmpl.template_content)
        return jinja_tmpl.render(**values)

    def delete_template(self, template_id: str) -> bool:
        return self._templates.pop(template_id, None) is not None


template_service = TemplateService()
