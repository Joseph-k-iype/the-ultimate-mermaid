from collections import defaultdict
from datetime import timezone

from fastapi import APIRouter, HTTPException, Query

from app.generators.base import filter_diagram_data
from app.models.requests import ScanRequest
from app.models.responses import DiagramResponse, ScanResponse
from app.services.scan_orchestrator import orchestrator, _MERMAID_GENERATORS

router = APIRouter(prefix="/scan", tags=["scan"])


@router.post("", response_model=ScanResponse)
def create_scan(req: ScanRequest) -> ScanResponse:
    return orchestrator.start_scan(req.repo_url, req.branch, req.perspectives)


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
        perspectives=state.requested_perspectives,
        components=list(state.components.keys()),
    )


@router.get("/{scan_id}/components")
def get_scan_components(scan_id: str):
    """Return detected components with entity counts."""
    state = orchestrator.get_scan(scan_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Scan not found")
    return {
        name: {"entity_count": len(ids), "entity_ids": ids}
        for name, ids in state.components.items()
    }


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
            "properties": {
                "entity_type": e.entity_type,
                "file_path": e.file_path,
                "component": e.metadata.get("component", ""),
            },
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


@router.get("/{scan_id}/manifest")
def get_manifest(scan_id: str):
    """Return a structured data manifest JSON for the scan."""
    state = orchestrator.get_scan(scan_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Scan not found")

    # Build entity-type counts
    type_counts: dict[str, int] = defaultdict(int)
    for e in state.entities:
        type_counts[e.entity_type] += 1

    # Build relationship index per entity
    outgoing: dict[str, list] = defaultdict(list)
    incoming: dict[str, list] = defaultdict(list)
    for r in state.relationships:
        outgoing[r.source_id].append({"target": r.target_id, "type": r.relationship_type})
        incoming[r.target_id].append({"source": r.source_id, "type": r.relationship_type})

    # Group entities by component
    comp_entities: dict[str, list] = defaultdict(list)
    for e in state.entities:
        comp = e.metadata.get("component", "ungrouped")
        entity_doc = {
            "name": e.name,
            "type": e.entity_type,
            "qualified_id": e.id,
            "location": {
                "file": e.file_path,
                "line": e.line_number,
            },
        }
        # Add schema info for classes/models
        attrs = e.metadata.get("attributes", [])
        methods = e.metadata.get("methods", [])
        if attrs:
            entity_doc["schema"] = {
                "fields": [
                    {"name": a.split(":")[0].strip(),
                     "type": a.split(":")[1].strip() if ":" in a else "Any"}
                    for a in attrs
                ]
            }
        if methods:
            entity_doc["methods"] = methods

        # Add endpoint info
        if e.entity_type == "endpoint":
            entity_doc["http_method"] = e.metadata.get("http_method", "")
            entity_doc["route"] = e.metadata.get("route", "")

        # Lineage
        out = outgoing.get(e.id, [])
        inc = incoming.get(e.id, [])
        if out or inc:
            entity_doc["lineage"] = {}
            if out:
                entity_doc["lineage"]["downstream"] = out
            if inc:
                entity_doc["lineage"]["upstream"] = inc

        comp_entities[comp].append(entity_doc)

    # Categorize types for summary
    _CATEGORY_MAP = {
        "class": "data_models", "model": "data_models",
        "endpoint": "endpoints",
        "function": "processing", "method": "processing",
        "db_read": "data_stores", "db_write": "data_stores",
        "file_reader": "file_io", "file_writer": "file_io",
        "consumer": "messaging", "producer": "messaging",
    }
    category_counts: dict[str, int] = defaultdict(int)
    for etype, count in type_counts.items():
        cat = _CATEGORY_MAP.get(etype, "other")
        category_counts[cat] += count

    return {
        "version": "1.0.0",
        "scan_id": state.scan_id,
        "repository": state.repo_url,
        "branch": state.branch,
        "generated_at": state.created_at.astimezone(timezone.utc).isoformat(),
        "summary": {
            "total_entities": len(state.entities),
            "total_relationships": len(state.relationships),
            "components": sorted(comp_entities.keys()),
            "categories": dict(category_counts),
            "entity_types": dict(type_counts),
        },
        "components": [
            {
                "name": comp,
                "entity_count": len(entities),
                "entities": sorted(entities, key=lambda x: (x["type"], x["name"])),
            }
            for comp, entities in sorted(comp_entities.items())
        ],
    }


@router.get("/{scan_id}/diagrams/{perspective}/data")
def get_diagram_data(
    scan_id: str,
    perspective: str,
    component: str | None = Query(None, description="Filter to a specific component"),
):
    """Return perspective-filtered entities and relationships as graph data."""
    state = orchestrator.get_scan(scan_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Scan not found")

    if perspective not in state.requested_perspectives:
        raise HTTPException(
            status_code=400,
            detail=f"Perspective '{perspective}' was not requested for this scan. "
                   f"Available: {', '.join(state.requested_perspectives)}",
        )

    dd = state.diagram_data.get(perspective)
    if dd is None:
        return {"nodes": [], "edges": []}

    # Apply component filter if specified (include 1-hop relationships)
    entities = dd.entities
    relationships = dd.relationships
    if component:
        # 1. Identify entities explicitly in the component
        core_ids = {e.id for e in entities if e.metadata.get("component") == component}
        
        # 2. Find any relationships touching a core entity
        filtered_rels = [
            r for r in relationships
            if r.source_id in core_ids or r.target_id in core_ids
        ]
        
        # 3. Identify all required entity IDs (core + 1-hop neighbors)
        required_ids = core_ids.copy()
        for r in filtered_rels:
            required_ids.add(r.source_id)
            required_ids.add(r.target_id)
            
        # 4. Filter lists
        entities = [e for e in entities if e.id in required_ids]
        relationships = filtered_rels

    nodes = [
        {
            "id": e.id,
            "label": e.name,
            "type": "CodeEntity",
            "properties": {
                "entity_type": e.entity_type,
                "file_path": e.file_path,
                "component": e.metadata.get("component", ""),
            },
        }
        for e in entities
    ]
    edges = [
        {
            "source": r.source_id,
            "target": r.target_id,
            "type": r.relationship_type,
            "properties": {},
        }
        for r in relationships
    ]
    return {"nodes": nodes, "edges": edges}


@router.get("/{scan_id}/diagrams/{perspective}", response_model=DiagramResponse)
def get_diagram(
    scan_id: str,
    perspective: str,
    component: str | None = Query(None, description="Filter to a specific component"),
) -> DiagramResponse:
    state = orchestrator.get_scan(scan_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Scan not found")

    if perspective not in state.requested_perspectives:
        raise HTTPException(
            status_code=400,
            detail=f"Perspective '{perspective}' was not requested for this scan. "
                   f"Available: {', '.join(state.requested_perspectives)}",
        )

    diagram = orchestrator.get_diagram(scan_id, perspective)
    if diagram is None:
        raise HTTPException(status_code=404, detail="Diagram not found")

    # When a component filter is active, regenerate mermaid from filtered data
    if component:
        dd = state.diagram_data.get(perspective)
        if dd:
            entities = dd.entities
            relationships = dd.relationships
            
            # 1. Identify entities explicitly in the component
            core_ids = {e.id for e in entities if e.metadata.get("component") == component}
            
            # 2. Find any relationships touching a core entity
            filtered_rels = [
                r for r in relationships
                if r.source_id in core_ids or r.target_id in core_ids
            ]
            
            # 3. Identify all required entity IDs
            required_ids = core_ids.copy()
            for r in filtered_rels:
                required_ids.add(r.source_id)
                required_ids.add(r.target_id)
            
            if required_ids:
                filtered_dd = filter_diagram_data(dd, required_ids)
                
                # Also filter the relationships explicitly to precisely match the 1-hop subset
                filtered_dd.relationships = filtered_rels
                
                gen = _MERMAID_GENERATORS.get(perspective)
                if gen:
                    diagram.mermaid_code = gen.generate(filtered_dd)

    return diagram
