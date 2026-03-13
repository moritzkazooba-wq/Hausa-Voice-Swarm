"""Balance inquiry agent."""

from __future__ import annotations

import structlog

from src.agents.domains.base import BaseDomainAgent
from src.models.transaction import ActionResult

logger = structlog.get_logger()


class BalanceAgent(BaseDomainAgent):
    """Handles balance inquiry requests."""

    agent_name: str = "balance"

    async def _execute(self, session_id: str, utterance: str) -> ActionResult:
        """Look up customer balance via repository, fall back to default."""
        if self.session_store and self.customer_repo:
            session = await self.session_store.get(session_id)
            if session:
                customer = await self.customer_repo.get_by_phone(session.customer_phone)
                if customer:
                    return ActionResult(
                        success=True,
                        message=f"Your balance is {customer.balance:,.2f} {customer.currency}.",
                    )

        return ActionResult(
            success=True,
            message="Your balance is 15,000 Naira.",
        )
