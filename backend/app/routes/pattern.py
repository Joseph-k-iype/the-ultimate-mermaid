from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.generators.base import filter_diagram_data
from app.models.domain import DiagramData
from app.models.pattern import (
    PatternCreateRequest,
    PatternResponse,
    PatternSearchResponse,
    PatternStatus,
    PatternUpdateRequest,
)
from app.services.pattern_service import pattern_service
from app.services.scan_orchestrator import orchestrator

router = APIRouter(prefix="/patterns", tags=["patterns"])


class StatusTransitionRequest(BaseModel):
    status: PatternStatus


class PublishFromScanRequest(BaseModel):
    title: str
    description: str
    owner: str
    tags: list[str] = Field(default_factory=list)
    perspectives: list[str] = Field(default_factory=list)
    content: str = ""
    component: str | None = None


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
def create_pattern_from_scan(scan_id: str, req: PublishFromScanRequest):
    scan = orchestrator.get_scan(scan_id)
    if scan is None:
        raise HTTPException(status_code=404, detail="Scan not found")

    perspectives_to_include = req.perspectives if req.perspectives else scan.requested_perspectives

    comp_entity_ids: set[str] | None = None
    if req.component:
        comp_entities_list = scan.components.get(req.component, [])
        if not comp_entities_list:
            raise HTTPException(status_code=400, detail=f"Component '{req.component}' not found")
        comp_entity_ids = set(comp_entities_list)

    # Collect mermaid blocks
    mermaid_blocks: dict[str, str] = {}
    for perspective in perspectives_to_include:
        code = scan.mermaid_code.get(perspective)
        if code and comp_entity_ids is not None:
            dd = scan.diagram_data.get(perspective)
            if dd:
                filtered_dd = filter_diagram_data(dd, comp_entity_ids)
                from app.services.scan_orchestrator import _MERMAID_GENERATORS
                gen = _MERMAID_GENERATORS.get(perspective)
                if gen:
                    code = gen.generate(filtered_dd)
        if code:
            mermaid_blocks[perspective] = code

    # Generate curated content from scan data
    content = req.content or _build_curated_content(scan, req, mermaid_blocks, comp_entity_ids)

    create_req = PatternCreateRequest(
        title=req.title,
        description=req.description,
        owner=req.owner,
        tags=req.tags,
        content=content,
        linked_scan_id=scan_id,
    )
    return pattern_service.create(create_req)


def _build_curated_content(
    scan,
    req,
    mermaid_blocks: dict[str, str],
    comp_filter: set[str] | None,
) -> str:
    """Build pattern content curated from actual scan data with enriched formatting."""
    from collections import Counter

    # Gather entities (optionally filtered)
    entities = scan.entities
    relationships = scan.relationships
    if comp_filter:
        entities = [e for e in entities if e.id in comp_filter]
        fids = {e.id for e in entities}
        relationships = [r for r in relationships if r.source_id in fids and r.target_id in fids]

    # Categorise
    components = sorted({e.metadata.get("component", "other") for e in entities if getattr(e, "metadata", None)} - {"other"})
    endpoints = [e for e in entities if e.entity_type == "endpoint"]
    classes = [e for e in entities if e.entity_type in ("class", "model")]
    stores = [e for e in entities if e.entity_type in ("db_read", "db_write")]
    messaging = [e for e in entities if e.entity_type in ("consumer", "producer")]

    lines: list[str] = []

    # 1. Title & Overview
    scope = f"Component: **{req.component}**" if req.component else f"Repository: `{scan.repo_url}`"
    lines.append(f"# {req.title}\n")
    if req.description:
        lines.append(f"_{req.description}_\n")
    
    lines.append("## Architecture Overview")
    lines.append(f"> Auto-generated from scan of {scope} (branch: `{scan.branch}`).")
    lines.append("")
    
    # 2. Visual Diagrams First
    if "er" in mermaid_blocks:
        lines.append("### Entity Relationships")
        lines.append("This diagram captures the domain models, classes, and their structural relationships.")
        lines.append(f"```mermaid\n{mermaid_blocks['er']}\n```\n")

    if "dataflow" in mermaid_blocks:
        lines.append("### Data Flow")
        lines.append("This diagram illustrates the end-to-end data movement from API entry points through processing layers to data stores.")
        lines.append(f"```mermaid\n{mermaid_blocks['dataflow']}\n```\n")

    # 3. System Metrics
    lines.append("## System Metrics")
    lines.append(f"- **Total Entities:** {len(entities)}")
    lines.append(f"- **Total Relationships:** {len(relationships)}")
    if components:
        lines.append(f"- **Detected Components:** {len(components)}")
    lines.append("")

    # 4. Components Structure
    if components:
        lines.append("## Component Breakdown")
        comp_entities = {}
        for e in entities:
            c = e.metadata.get("component", "other")
            comp_entities.setdefault(c, []).append(e)
            
        for c in components:
            ents = comp_entities.get(c, [])
            etypes = Counter(e.entity_type for e in ents)
            summary = ", ".join(f"{v} {k.capitalize()}s" for k, v in sorted(etypes.items()))
            lines.append(f"- **{c}**")
            lines.append(f"  - Contained entities: {len(ents)} ({summary})")
        lines.append("")

    # 5. API Endpoints
    if endpoints:
        lines.append("## API Endpoints")
        lines.append("| Method | Route | Implementation |")
        lines.append("|:-------|:------|:---------------|")
        for ep in sorted(endpoints, key=lambda e: e.name):
            method = ep.metadata.get("http_method", "ANY").upper()
            route = ep.metadata.get("route", ep.name)
            handler = f"`{ep.file_path}:{ep.line_number}`"
            # Highlight methods
            method_badge = f"**{method}**"
            lines.append(f"| {method_badge} | `{route}` | {handler} |")
        lines.append("")

    # 6. Data Models
    if classes:
        lines.append("## Data Models & Schema")
        for cls in sorted(classes, key=lambda e: e.name):
            lines.append(f"### `{cls.name}`")
            lines.append(f"> Defined in `{cls.file_path}:{cls.line_number}`\n")
            
            attrs = cls.metadata.get("attributes", [])
            if attrs:
                lines.append("#### Schema Properties")
                lines.append("| Property | Type |")
                lines.append("|:---------|:-----|")
                for a in attrs:
                    parts = a.split(":", 1)
                    name = parts[0].strip()
                    ftype = parts[1].strip() if len(parts) > 1 else "Any"
                    lines.append(f"| **{name}** | `{ftype}` |")
                lines.append("")
                
            methods = cls.metadata.get("methods", [])
            if methods:
                lines.append("#### Behaviors")
                lines.append("- " + "\n- ".join(f"`{m}()`" for m in methods))
                lines.append("")

    # 7. Data Stores
    if stores:
        lines.append("## Data Operations")
        lines.append("| Operation | Target | Source Location |")
        lines.append("|:----------|:-------|:----------------|")
        for st in sorted(stores, key=lambda e: e.name):
            op_type = "Write/Update" if st.entity_type == "db_write" else "Read/Query"
            lines.append(f"| {op_type} | `{st.name}` | `{st.file_path}:{st.line_number}` |")
        lines.append("")

    return "\n".join(lines)


