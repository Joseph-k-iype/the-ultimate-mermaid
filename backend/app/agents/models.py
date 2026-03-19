"""Pydantic models for the PatternViz multi-agent system."""

from datetime import datetime, timezone
from enum import StrEnum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from app.models.domain import CodeEntity, Relationship  # noqa: F401


# ---------------------------------------------------------------------------
# Agent-to-Agent (A2A) messaging
# ---------------------------------------------------------------------------

class A2AMessageType(StrEnum):
    """Types of messages exchanged between agents."""

    task_assignment = "task_assignment"
    task_result = "task_result"
    validation_request = "validation_request"
    validation_response = "validation_response"
    context_share = "context_share"
    feedback = "feedback"
    error = "error"


class A2AMessage(BaseModel):
    """A single message passed between two agents."""

    message_id: str = Field(default_factory=lambda: str(uuid4()))
    type: A2AMessageType
    source_agent: str
    target_agent: str
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    payload: dict
    correlation_id: str = Field(default_factory=lambda: str(uuid4()))
    context: dict = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Agent analysis outputs
# ---------------------------------------------------------------------------

INSIGHT_CATEGORIES = Literal[
    "data_flow",
    "service_flow",
    "architecture",
    "code_quality",
    "security",
    "sdlc",
    "performance",
]

SEVERITY_LEVELS = Literal["info", "warning", "critical"]


class AgentInsight(BaseModel):
    """A single insight produced by an agent."""

    agent_name: str
    category: INSIGHT_CATEGORIES
    title: str
    description: str
    severity: SEVERITY_LEVELS
    evidence: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)


class DetectedPattern(BaseModel):
    """A structural or behavioural pattern detected across the codebase."""

    pattern_type: str
    description: str
    entities_involved: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    related_perspectives: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Per-agent and overall run results
# ---------------------------------------------------------------------------

class AgentOutput(BaseModel):
    """Output produced by a single agent."""

    insights: list[AgentInsight] = Field(default_factory=list)
    patterns: list[DetectedPattern] = Field(default_factory=list)
    summary: str = ""
    status: Literal["success", "partial", "failed"] = "success"


class AgentRunResult(BaseModel):
    """Aggregated result of a complete multi-agent run."""

    scan_id: str
    run_id: str = Field(default_factory=lambda: str(uuid4()))
    status: Literal["success", "partial", "failed"]
    started_at: datetime
    completed_at: datetime | None = None
    insights: list[AgentInsight] = Field(default_factory=list)
    patterns: list[DetectedPattern] = Field(default_factory=list)
    agent_summaries: dict[str, str] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)
