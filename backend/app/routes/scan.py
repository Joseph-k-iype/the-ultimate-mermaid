from fastapi import APIRouter, HTTPException

from app.models.requests import ScanRequest
from app.models.responses import DiagramResponse, ScanResponse
from app.services.scan_orchestrator import PERSPECTIVES, orchestrator

router = APIRouter(prefix="/scan", tags=["scan"])


@router.post("", response_model=ScanResponse)
def create_scan(req: ScanRequest) -> ScanResponse:
    return orchestrator.start_scan(req.repo_url, req.branch)


@router.get("", response_model=list[ScanResponse])
def list_scans() -> list[ScanResponse]:
    return orchestrator.list_scans()


@router.delete("", status_code=204)
def delete_all_scans():
    """Clear all scan data and reset FalkorDB graph."""
    orchestrator._scans.clear()

    # Also clear the FalkorDB graph data
    try:
        from app.graph import graph_service

        if graph_service.is_available:
            graph_service.clear_all()
    except Exception:
        pass  # Non-fatal if graph cleanup fails

    return None


@router.get("/{scan_id}", response_model=ScanResponse)
def get_scan(scan_id: str) -> ScanResponse:
    state = orchestrator.get_scan(scan_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Scan not found")
    return ScanResponse(
        scan_id=state.scan_id,
        status=state.status,
        repo_url=state.repo_url,
        branch=state.branch,
        created_at=state.created_at,
    )


@router.get("/{scan_id}/entities")
def get_scan_entities(scan_id: str):
    """Return raw entities and relationships for a scan (for graph visualization)."""
    state = orchestrator.get_scan(scan_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Scan not found")

    nodes = [
        {
            "id": e.id,
            "label": e.name,
            "type": "CodeEntity",
            "properties": {"entity_type": e.entity_type, "file_path": e.file_path},
        }
        for e in state.entities
    ]
    edges = [
        {
            "source": r.source_id,
            "target": r.target_id,
            "type": r.relationship_type,
            "properties": {},
        }
        for r in state.relationships
    ]
    return {"nodes": nodes, "edges": edges}


@router.get("/{scan_id}/diagrams/{perspective}", response_model=DiagramResponse)
def get_diagram(scan_id: str, perspective: str) -> DiagramResponse:
    if perspective not in PERSPECTIVES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid perspective. Must be one of: {', '.join(PERSPECTIVES)}",
        )
    diagram = orchestrator.get_diagram(scan_id, perspective)
    if diagram is None:
        raise HTTPException(status_code=404, detail="Diagram not found")
    return diagram
