"""Shared state definition for LangGraph orchestrator-worker pattern."""

from __future__ import annotations

from typing import TypedDict


class AgentState(TypedDict):
    """Typed state flowing through the LangGraph orchestrator graph.

    Each node reads/writes fields as needed; the graph carries this dict
    from START through classification → routing → domain agent → END.
    """

    session_id: str
    utterance: str
    intent: str
    confidence: float
    classifier_type: str
    response: str
    requires_confirmation: bool
    success: bool
