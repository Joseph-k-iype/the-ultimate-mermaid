"""Agent analysis API endpoints."""

import logging

from fastapi import APIRouter, HTTPException

from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents", tags=["agents"])


def _check_agents_enabled():
    if not settings.ENABLE_AGENTS:
        raise HTTPException(
            status_code=503,
            detail="Agent analysis is not enabled. Set PATTERNVIZ_ENABLE_AGENTS=true.",
        )


def _get_scan_state(scan_id: str):
    from app.services.scan_orchestrator import orchestrator

    state = orchestrator.get_scan(scan_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"Scan {scan_id} not found")
    if state.status != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Scan {scan_id} is not completed (status: {state.status})",
        )
    return state


@router.post("/analyze/{scan_id}")
def trigger_agent_analysis(scan_id: str):
    """Trigger multi-agent AI analysis on a completed scan."""
    _check_agents_enabled()
    state = _get_scan_state(scan_id)

    from app.agents.orchestration import agent_orchestration

    result = agent_orchestration.analyze(state)
    # Cache the result on the scan state
    state.agent_insights = result.model_dump()
    return result.model_dump()


@router.get("/insights/{scan_id}")
def get_agent_insights(scan_id: str):
    """Get all agent insights for a completed scan."""
    _check_agents_enabled()
    state = _get_scan_state(scan_id)

    insights = getattr(state, "agent_insights", None)
    if not insights:
        raise HTTPException(
            status_code=404,
            detail=f"No agent insights found for scan {scan_id}. Trigger analysis first.",
        )
    return insights


@router.get("/insights/{scan_id}/{category}")
def get_agent_insights_by_category(scan_id: str, category: str):
    """Get agent insights filtered by category."""
    _check_agents_enabled()
    state = _get_scan_state(scan_id)

    valid_categories = {
        "data_flow",
        "service_flow",
        "architecture",
        "code_quality",
        "security",
        "sdlc",
        "performance",
    }
    if category not in valid_categories:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category '{category}'. Must be one of: {sorted(valid_categories)}",
        )

    insights = getattr(state, "agent_insights", None)
    if not insights:
        raise HTTPException(
            status_code=404,
            detail=f"No agent insights found for scan {scan_id}. Trigger analysis first.",
        )

    # Filter insights by category
    filtered = dict(insights)
    if "insights" in filtered:
        filtered["insights"] = [
            i for i in filtered["insights"] if i.get("category") == category
        ]
    return filtered
