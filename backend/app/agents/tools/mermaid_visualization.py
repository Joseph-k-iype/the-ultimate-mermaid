"""Mermaid visualization agent tool."""

import json
import logging
from pathlib import Path

from app.agents.models import AgentOutput, AgentInsight, DetectedPattern
from app.agents.llm_adapter import get_llm, AgentDisabledError

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def analyze_mermaid(state: dict) -> AgentOutput:
    """Generate Mermaid diagrams from the codebase analysis."""
    from app.agents.tools._base import load_prompt, serialize_context

    try:
        llm = get_llm()
        system_prompt = load_prompt("mermaid_visualization.md")
        context = serialize_context(state)

        user_message = (
            "Generate Mermaid diagrams for the following codebase:\n\n" + context
        )

        response = llm.invoke(system_prompt, user_message)
        return _parse_mermaid_response(response)

    except AgentDisabledError:
        return AgentOutput(
            summary="mermaid_visualization skipped: AI service not available",
            status="failed",
        )
    except Exception as exc:
        # Retry once
        try:
            llm = get_llm()
            system_prompt = load_prompt("mermaid_visualization.md")
            context = serialize_context(state)
            user_message = (
                f"Previous attempt failed: {exc}. Return valid JSON.\n\n"
                "Generate Mermaid diagrams for the following codebase:\n\n" + context
            )
            response = llm.invoke(system_prompt, user_message)
            return _parse_mermaid_response(response)
        except Exception as retry_exc:
            logger.warning("Mermaid agent failed after retry: %s", retry_exc)
            return AgentOutput(
                summary=f"mermaid_visualization failed: {retry_exc}",
                status="failed",
            )


def _parse_mermaid_response(response: str) -> AgentOutput:
    """Parse the mermaid agent response, extracting diagrams as patterns."""
    text = response.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines[1:] if not l.strip().startswith("```")]
        text = "\n".join(lines)

    data = json.loads(text)

    # Convert diagrams to DetectedPattern entries for frontend rendering
    patterns = []
    diagrams = data.get("diagrams", [])
    for d in diagrams:
        patterns.append(
            DetectedPattern(
                pattern_type=f"diagram:{d.get('diagram_type', 'flowchart')}",
                description=d.get("title", "Diagram"),
                entities_involved=[],
                confidence=1.0,
                related_perspectives=[d.get("mermaid_code", "")],
            )
        )

    return AgentOutput(
        insights=data.get("insights", []),
        patterns=patterns,
        summary=data.get("summary", "Mermaid diagrams generated"),
        status=data.get("status", "success"),
    )
