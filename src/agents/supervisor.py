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
from src.db.repositories import CustomerRepository
from src.db.session_store import SessionStore
from src.events.producer import KafkaEventProducer
from src.events.session_events import emit_intent_classified, emit_tool_executed
from src.metrics.definitions import agent_routing_total
from src.models.transaction import ActionResult

logger = structlog.get_logger()

# Shared services — initialized lazily or injected from app lifespan
_session_store: SessionStore | None = None
_customer_repo: CustomerRepository | None = None
_kafka_producer: KafkaEventProducer | None = None


def configure_supervisor(
    *,
    session_store: SessionStore | None = None,
    customer_repo: CustomerRepository | None = None,
    kafka_producer: KafkaEventProducer | None = None,
) -> None:
    """Inject shared services into the supervisor (called from app lifespan)."""
    global _session_store, _customer_repo, _kafka_producer
    _session_store = session_store
    _customer_repo = customer_repo
    _kafka_producer = kafka_producer


def _build_agent_map() -> dict[str, BaseDomainAgent]:
    """Build agent map with injected dependencies."""
    return {
        "balance": BalanceAgent(session_store=_session_store, customer_repo=_customer_repo),
        "transfer": TransferAgent(session_store=_session_store, customer_repo=_customer_repo),
        "bills": BillsAgent(session_store=_session_store, customer_repo=_customer_repo),
        "general": GeneralAgent(session_store=_session_store, customer_repo=_customer_repo),
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

    # Emit intent classification event
    if _kafka_producer is not None:
        await emit_intent_classified(
            _kafka_producer,
            session_id=session_id,
            utterance=utterance,
            intent=classification.intent,
            confidence=classification.confidence,
            language="ha",
            model_used=classification.classifier_type,
        )

    agent_map = _build_agent_map()
    agent = agent_map.get(target_agent, agent_map["general"])
    result = await agent.run(session_id, utterance)

    # Emit tool execution event
    if _kafka_producer is not None:
        await emit_tool_executed(
            _kafka_producer,
            session_id=session_id,
            agent_name=agent.agent_name,
            tool_name=f"{agent.agent_name}_execute",
            success=result.success,
            duration_ms=classification.elapsed_ms,
            result_summary=result.message[:100],
        )

    await logger.ainfo(
        "supervisor_routed",
        session_id=session_id,
        target_agent=target_agent,
        confidence=classification.confidence,
        success=result.success,
    )

    return result, classification
