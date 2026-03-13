"""Supervisor that routes utterances to domain agents via LangGraph orchestrator.

Wraps the LangGraph StateGraph execution and converts the result back to
the ``(ActionResult, ClassificationResult)`` tuple expected by callers.
"""

from __future__ import annotations

import structlog

from src.agents.intent import ClassificationResult
from src.agents.orchestrator import run_orchestrator
from src.models.transaction import ActionResult

logger = structlog.get_logger()


async def route_to_agent(
    session_id: str,
    utterance: str,
) -> tuple[ActionResult, ClassificationResult]:
    """Classify intent and route to the appropriate domain agent.

    Delegates to the LangGraph orchestrator graph, then maps the final
    state back to ``ActionResult`` and ``ClassificationResult``.
    """
    state = await run_orchestrator(session_id, utterance)

    action_result = ActionResult(
        success=state["success"],
        message=state["response"],
        requires_confirmation=state["requires_confirmation"],
    )

    classification = ClassificationResult(
        intent=state["intent"],  # type: ignore[arg-type]
        confidence=state["confidence"],
        utterance=state["utterance"],
        classifier_type=state["classifier_type"],
        elapsed_ms=0.0,  # timing captured in the graph nodes
    )

    await logger.ainfo(
        "supervisor_routed",
        session_id=session_id,
        target_agent=state["intent"],
        confidence=state["confidence"],
        success=state["success"],
    )

    return action_result, classification
