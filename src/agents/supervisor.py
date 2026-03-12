"""Supervisor that routes utterances to domain agents via intent classification.

Uses the orchestrator-worker pattern: the supervisor classifies intent, then
delegates to the appropriate domain agent.
"""

from __future__ import annotations

import structlog

from src.agents.domains.balance import BalanceAgent
from src.agents.domains.base import BaseDomainAgent
from src.agents.domains.bills import BillsAgent
from src.agents.domains.general import GeneralAgent
from src.agents.domains.transfer import TransferAgent
from src.agents.intent import ClassificationResult, classify_intent
from src.metrics.definitions import agent_routing_total
from src.models.transaction import ActionResult

logger = structlog.get_logger()

# Map intent labels to agent instances
_AGENT_MAP: dict[str, BaseDomainAgent] = {
    "balance": BalanceAgent(),
    "transfer": TransferAgent(),
    "bills": BillsAgent(),
    "general": GeneralAgent(),
}


async def route_to_agent(
    session_id: str,
    utterance: str,
) -> tuple[ActionResult, ClassificationResult]:
    """Classify intent and route to the appropriate domain agent.

    Returns both the action result and the classification result for
    downstream consumers (e.g. Kafka events, metrics).
    """
    classification = await classify_intent(utterance)
    target_agent = classification.intent

    agent_routing_total.labels(target_agent=target_agent).inc()

    agent = _AGENT_MAP.get(target_agent, _AGENT_MAP["general"])
    result = await agent.run(session_id, utterance)

    await logger.ainfo(
        "supervisor_routed",
        session_id=session_id,
        target_agent=target_agent,
        confidence=classification.confidence,
        success=result.success,
    )

    return result, classification
