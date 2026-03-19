"""LangGraph StateGraph workflow builder for multi-agent orchestration."""

import logging
from functools import partial

from app.agents.state import AgentState
from app.agents.graph.nodes import (
    supervisor_node,
    coordinator_node,
    specialist_node,
    aggregator_node,
)

logger = logging.getLogger(__name__)

# All possible specialist agent names
ALL_SPECIALISTS = [
    "data_flow",
    "service_flow",
    "architecture",
    "code_quality",
    "security",
    "sdlc",
    "performance",
]


def build_agent_graph():
    """
    Build the LangGraph compiled graph for agent orchestration.

    Flow:
        START -> supervisor -> coordinator -> [specialists in sequence] -> aggregator -> END

    Returns a callable that accepts AgentState and returns the final state.
    Falls back to a simple sequential runner if langgraph is not installed.
    """
    try:
        from langgraph.graph import StateGraph, END

        graph = StateGraph(AgentState)

        # Add core nodes
        graph.add_node("supervisor", supervisor_node)
        graph.add_node("coordinator", coordinator_node)
        graph.add_node("aggregator", aggregator_node)

        # Add specialist nodes
        for name in ALL_SPECIALISTS:
            graph.add_node(
                f"specialist_{name}",
                partial(specialist_node, agent_name=name),
            )

        # Set entry point
        graph.set_entry_point("supervisor")

        # supervisor -> coordinator
        graph.add_edge("supervisor", "coordinator")

        # coordinator -> dynamic routing to specialists
        def route_after_coordinator(state: AgentState) -> str:
            """Route to first selected specialist or aggregator."""
            selected = state.get("selected_agents", [])
            if selected:
                return f"specialist_{selected[0]}"
            return "aggregator"

        targets = {
            f"specialist_{name}": f"specialist_{name}"
            for name in ALL_SPECIALISTS
        }
        targets["aggregator"] = "aggregator"
        graph.add_conditional_edges(
            "coordinator", route_after_coordinator, targets,
        )

        # Chain specialists sequentially based on selected_agents
        for name in ALL_SPECIALISTS:

            def route_next_specialist(
                state: AgentState, current_name: str = name,
            ) -> str:
                selected = state.get("selected_agents", [])
                if current_name in selected:
                    idx = selected.index(current_name)
                    if idx + 1 < len(selected):
                        return f"specialist_{selected[idx + 1]}"
                return "aggregator"

            next_targets = {
                f"specialist_{n}": f"specialist_{n}"
                for n in ALL_SPECIALISTS
            }
            next_targets["aggregator"] = "aggregator"
            graph.add_conditional_edges(
                f"specialist_{name}", route_next_specialist, next_targets,
            )

        # aggregator -> END
        graph.add_edge("aggregator", END)

        compiled = graph.compile()
        logger.info("LangGraph workflow compiled successfully")
        return compiled

    except ImportError:
        logger.warning(
            "langgraph not installed, using fallback sequential runner",
        )
        return _fallback_runner


def _fallback_runner(state: AgentState) -> AgentState:
    """Simple sequential fallback when langgraph is not available."""
    state = dict(state)

    # Run supervisor
    updates = supervisor_node(state)
    state.update(updates)

    # Run coordinator
    updates = coordinator_node(state)
    state.update(updates)

    # Run selected specialists
    for agent_name in state.get("selected_agents", []):
        updates = specialist_node(state, agent_name)
        state.update(updates)

    # Run aggregator
    updates = aggregator_node(state)
    state.update(updates)

    return state
