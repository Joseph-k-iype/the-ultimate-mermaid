"""LangGraph state schema for the PatternViz multi-agent orchestrator."""

from typing import TypedDict

from app.agents.models import A2AMessage, AgentOutput


class AgentState(TypedDict, total=False):
    """Shared state passed through the LangGraph agent graph.

    Using ``total=False`` so that every key is optional — nodes only
    need to populate the keys they care about.
    """

    # ---- inputs ----
    scan_id: str
    entities: list[dict]  # serialized CodeEntity dicts
    relationships: list[dict]  # serialized Relationship dicts

    # ---- derived context ----
    components: dict[str, list[str]]
    mermaid_code: dict[str, str]

    # ---- inter-agent communication ----
    messages: list[A2AMessage]
    agent_outputs: dict[str, AgentOutput]

    # ---- orchestration metadata ----
    current_task: str
    retry_count: int
    errors: list[str]
    selected_agents: list[str]
