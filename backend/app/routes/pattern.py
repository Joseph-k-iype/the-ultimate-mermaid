from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.models.pattern import (
    PatternCreateRequest,
    PatternResponse,
    PatternSearchResponse,
    PatternStatus,
    PatternUpdateRequest,
)
from app.services.pattern_service import pattern_service
from app.services.scan_orchestrator import PERSPECTIVES, orchestrator

router = APIRouter(prefix="/patterns", tags=["patterns"])


class StatusTransitionRequest(BaseModel):
    status: PatternStatus


@router.post("", response_model=PatternResponse, status_code=201)
def create_pattern(req: PatternCreateRequest):
    return pattern_service.create(req)


@router.get("", response_model=PatternSearchResponse)
def search_patterns(
    query: str | None = Query(None),
    tags: list[str] | None = Query(None),
    status: PatternStatus | None = Query(None),
    owner: str | None = Query(None),
):
    return pattern_service.search(query=query, tags=tags, status=status, owner=owner)


@router.get("/template")
def get_system_design_template():
    return {"content": pattern_service.get_system_design_template()}


@router.get("/{pattern_id}", response_model=PatternResponse)
def get_pattern(pattern_id: str):
    result = pattern_service.get(pattern_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Pattern not found")
    return result


@router.put("/{pattern_id}", response_model=PatternResponse)
def update_pattern(pattern_id: str, req: PatternUpdateRequest):
    result = pattern_service.update(pattern_id, req)
    if result is None:
        raise HTTPException(status_code=404, detail="Pattern not found")
    return result


@router.delete("/{pattern_id}", status_code=204)
def delete_pattern(pattern_id: str):
    if not pattern_service.delete(pattern_id):
        raise HTTPException(status_code=404, detail="Pattern not found")


@router.post("/{pattern_id}/transition", response_model=PatternResponse)
def transition_status(pattern_id: str, req: StatusTransitionRequest):
    try:
        result = pattern_service.transition_status(pattern_id, req.status)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if result is None:
        raise HTTPException(status_code=404, detail="Pattern not found")
    return result


@router.post("/from-scan/{scan_id}", response_model=PatternResponse, status_code=201)
def create_pattern_from_scan(scan_id: str, req: PatternCreateRequest):
    scan = orchestrator.get_scan(scan_id)
    if scan is None:
        raise HTTPException(status_code=404, detail="Scan not found")

    # Collect mermaid blocks from all perspectives
    mermaid_sections: list[str] = []
    for perspective in PERSPECTIVES:
        code = scan.mermaid_code.get(perspective)
        if code:
            mermaid_sections.append(
                f"## {perspective.title()} Diagram\n\n```mermaid\n{code}\n```"
            )

    # Inject into template content or append to provided content
    content = req.content or pattern_service.get_system_design_template()
    if mermaid_sections:
        content += "\n\n" + "\n\n".join(mermaid_sections)

    # Override the request content and set linked_scan_id
    create_req = PatternCreateRequest(
        title=req.title,
        description=req.description,
        owner=req.owner,
        tags=req.tags,
        content=content,
        linked_scan_id=scan_id,
    )
    return pattern_service.create(create_req)
