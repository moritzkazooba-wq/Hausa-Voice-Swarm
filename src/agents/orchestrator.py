"""LangGraph StateGraph orchestrator — routes utterances through domain agents.

Implements the orchestrator-worker pattern:
  START → classify (intent) → conditional edge → domain agent node → END

Each node reads/writes the shared ``AgentState`` TypedDict.
"""

from __future__ import annotations

import structlog
from langgraph.graph import END, START, StateGraph

from src.agents.base import AgentState
from src.agents.domains.balance import BalanceAgent
from src.agents.domains.bills import BillsAgent
from src.agents.domains.general import GeneralAgent
from src.agents.domains.transfer import TransferAgent
from src.agents.intent import classify_intent
from src.metrics.definitions import agent_routing_total

logger = structlog.get_logger()

# Singleton domain agent instances (stateless, safe to share)
_balance_agent = BalanceAgent()
_transfer_agent = TransferAgent()
_bills_agent = BillsAgent()
_general_agent = GeneralAgent()


# ---------------------------------------------------------------------------
# Graph nodes
# ---------------------------------------------------------------------------


async def classify_node(state: AgentState) -> AgentState:
    """Classify the utterance and write intent fields into state."""
    result = await classify_intent(state["utterance"])
    agent_routing_total.labels(target_agent=result.intent).inc()
    return {
        **state,
        "intent": result.intent,
        "confidence": result.confidence,
        "classifier_type": result.classifier_type,
    }


async def balance_node(state: AgentState) -> AgentState:
    """Execute the balance agent."""
    result = await _balance_agent.run(state["session_id"], state["utterance"])
    return {
        **state,
        "response": result.message,
        "requires_confirmation": result.requires_confirmation or False,
        "success": result.success,
    }


async def transfer_node(state: AgentState) -> AgentState:
    """Execute the transfer agent."""
    result = await _transfer_agent.run(state["session_id"], state["utterance"])
    return {
        **state,
        "response": result.message,
        "requires_confirmation": result.requires_confirmation or False,
        "success": result.success,
    }


async def bills_node(state: AgentState) -> AgentState:
    """Execute the bills agent."""
    result = await _bills_agent.run(state["session_id"], state["utterance"])
    return {
        **state,
        "response": result.message,
        "requires_confirmation": result.requires_confirmation or False,
        "success": result.success,
    }


async def general_node(state: AgentState) -> AgentState:
    """Execute the general agent."""
    result = await _general_agent.run(state["session_id"], state["utterance"])
    return {
        **state,
        "response": result.message,
        "requires_confirmation": result.requires_confirmation or False,
        "success": result.success,
    }


# ---------------------------------------------------------------------------
# Conditional routing
# ---------------------------------------------------------------------------

_INTENT_TO_NODE: dict[str, str] = {
    "balance": "balance",
    "transfer": "transfer",
    "bills": "bills",
    "general": "general",
}


def route_by_intent(state: AgentState) -> str:
    """Return the next node name based on the classified intent."""
    return _INTENT_TO_NODE.get(state["intent"], "general")


# ---------------------------------------------------------------------------
# Build and compile the graph
# ---------------------------------------------------------------------------


def build_orchestrator_graph() -> StateGraph[AgentState]:
    """Construct the LangGraph StateGraph (uncompiled)."""
    graph: StateGraph[AgentState] = StateGraph(AgentState)

    # Add nodes
    graph.add_node("classify", classify_node)
    graph.add_node("balance", balance_node)
    graph.add_node("transfer", transfer_node)
    graph.add_node("bills", bills_node)
    graph.add_node("general", general_node)

    # Edges: START → classify → conditional → agent → END
    graph.add_edge(START, "classify")
    graph.add_conditional_edges(
        "classify",
        route_by_intent,
        list(_INTENT_TO_NODE.values()),
    )
    graph.add_edge("balance", END)
    graph.add_edge("transfer", END)
    graph.add_edge("bills", END)
    graph.add_edge("general", END)

    return graph


# Pre-compiled graph ready for invocation
orchestrator_graph = build_orchestrator_graph().compile()


async def run_orchestrator(session_id: str, utterance: str) -> AgentState:
    """Run the full orchestrator graph and return the final state."""
    initial_state: AgentState = {
        "session_id": session_id,
        "utterance": utterance,
        "intent": "",
        "confidence": 0.0,
        "classifier_type": "",
        "response": "",
        "requires_confirmation": False,
        "success": False,
    }
    result = await orchestrator_graph.ainvoke(initial_state)  # type: ignore[arg-type]
    await logger.ainfo(
        "orchestrator_completed",
        session_id=session_id,
        intent=result["intent"],
        confidence=result["confidence"],
        success=result["success"],
    )
    return result  # type: ignore[return-value]
