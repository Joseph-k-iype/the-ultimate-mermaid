"""Graph API endpoints for knowledge graph visualization and concept hierarchy."""

from fastapi import APIRouter, Query

from app.graph import graph_service
from app.models.graph import (
    ConceptHierarchyResponse,
    ConceptNode,
    GraphEdge,
    GraphNode,
    GraphStatusResponse,
    KnowledgeGraphResponse,
)

router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("/status", response_model=GraphStatusResponse)
def get_graph_status():
    """FalkorDB connection status and node/edge counts."""
    stats = graph_service.get_stats()
    return GraphStatusResponse(
        available=graph_service.is_available,
        node_count=stats.get("total_nodes", 0),
        edge_count=stats.get("total_edges", 0),
        details=stats,
    )


@router.get("/knowledge", response_model=KnowledgeGraphResponse)
def get_knowledge_graph(scan_id: str = Query(..., description="Scan ID to visualize")):
    """Knowledge graph for a specific scan.

    Each scan produces its own isolated graph. Falls back to in-memory
    scan data when FalkorDB is unavailable.
    """
    data = graph_service.get_knowledge_graph(scan_id)
    nodes = [GraphNode(**n) for n in data.get("nodes", [])]
    edges = [GraphEdge(**e) for e in data.get("edges", [])]

    # Fallback: pull from in-memory scan data if graph returned nothing
    if not nodes:
        from app.services.scan_orchestrator import orchestrator

        state = orchestrator.get_scan(scan_id)
        if state is not None:
            node_set: set[str] = set()
            for e in state.entities[:5000]:
                if e.id not in node_set:
                    node_set.add(e.id)
                    nodes.append(GraphNode(
                        id=e.id,
                        label=e.name,
                        type="CodeEntity",
                        properties={
                            "entity_type": e.entity_type,
                            "file_path": e.file_path,
                            "component": e.metadata.get("component", ""),
                        },
                    ))
            for r in state.relationships:
                if r.source_id in node_set and r.target_id in node_set:
                    edges.append(GraphEdge(
                        source=r.source_id,
                        target=r.target_id,
                        type=r.relationship_type,
                        properties={},
                    ))

    stats = {"total_nodes": len(nodes), "total_edges": len(edges)}
    return KnowledgeGraphResponse(nodes=nodes, edges=edges, stats=stats)


@router.get("/concepts", response_model=ConceptHierarchyResponse)
def get_concept_hierarchy():
    """SKOS concept hierarchy tree."""
    raw = graph_service.get_concepts()
    concepts = [ConceptNode(**c) for c in raw]
    return ConceptHierarchyResponse(concepts=concepts)


@router.get("/patterns/{pattern_id}/related")
def get_related_patterns(pattern_id: str):
    """Patterns related by shared tags, scans, or entities."""
    related = graph_service.find_related_patterns(pattern_id)
    return {"results": related, "total": len(related)}


@router.get("/stats")
def get_graph_stats():
    """Detailed node/edge count breakdown."""
    return graph_service.get_stats()
