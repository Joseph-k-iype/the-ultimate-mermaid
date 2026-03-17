from fastapi import APIRouter, HTTPException

from app.models.requests import TemplateCreateRequest, TemplateRenderRequest
from app.models.responses import TemplateResponse
from app.services.template_service import template_service

router = APIRouter(prefix="/templates", tags=["templates"])


@router.post("", response_model=TemplateResponse)
def create_template(req: TemplateCreateRequest) -> TemplateResponse:
    return template_service.create_template(req)


@router.get("", response_model=list[TemplateResponse])
def list_templates() -> list[TemplateResponse]:
    return template_service.list_templates()


@router.get("/{template_id}", response_model=TemplateResponse)
def get_template(template_id: str) -> TemplateResponse:
    tmpl = template_service.get_template(template_id)
    if tmpl is None:
        raise HTTPException(status_code=404, detail="Template not found")
    return tmpl


@router.post("/{template_id}/render")
def render_template(template_id: str, req: TemplateRenderRequest) -> dict:
    result = template_service.render_template(template_id, req.values)
    if result is None:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"rendered": result}


@router.delete("/{template_id}", status_code=204)
def delete_template(template_id: str) -> None:
    if not template_service.delete_template(template_id):
        raise HTTPException(status_code=404, detail="Template not found")
