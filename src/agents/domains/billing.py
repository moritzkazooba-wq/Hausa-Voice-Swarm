"""Billing agent: balance_check, transaction_history, payment, dispute."""

from typing import Any, ClassVar

import structlog

from src.agents.domains.base import DomainAgent

logger = structlog.get_logger()

# GraphQL operations
BALANCE_QUERY = """
query AccountBalance($phoneNumber: String!) {
    accountBalance(phoneNumber: $phoneNumber) {
        id
        phoneNumber
        name
        balance
        currency
        plan
        status
        region
    }
}
"""

TRANSACTION_QUERY = """
query TransactionHistory($accountId: ID!, $last: Int) {
    transactionHistory(accountId: $accountId, last: $last) {
        id
        accountId
        amount
        merchant
        date
        status
        type
    }
}
"""

PAYMENT_MUTATION = """
mutation ProcessPayment($phoneNumber: String!, $amount: Float!, $merchant: String!) {
    processPayment(phoneNumber: $phoneNumber, amount: $amount, merchant: $merchant) {
        success
        message
        referenceId
        requiresConfirmation
    }
}
"""

ESCALATION_MUTATION = """
mutation CreateEscalationTicket($phoneNumber: String!, $issue: String!) {
    createEscalationTicket(phoneNumber: $phoneNumber, issue: $issue) {
        success
        message
        referenceId
        requiresConfirmation
    }
}
"""


class BillingAgent(DomainAgent):
    """Handles balance inquiries, transaction history, payments, and disputes.

    - balance_check, transaction_history: gemini-flash (simple)
    - payment: gemini-flash with confirmation required
    - dispute: gpt-4o (complex), escalates to ticket
    """

    name = "billing_agent"
    description = "Handles billing: balance, transactions, payments, disputes"
    handled_intents: ClassVar[list[str]] = [
        "balance_check", "transaction_history", "payment", "dispute",
    ]
    available_tools: ClassVar[list[str]] = [
        "accountBalance", "transactionHistory", "processPayment",
        "createEscalationTicket",
    ]

    def _select_model(self, intent: str) -> str:
        """Use gpt-4o for disputes, gemini-flash for everything else."""
        from src.config import LLMSettings
        settings = LLMSettings(_env_file=None)
        if intent == "dispute":
            return settings.complex_model
        return settings.default_model

    async def handle(self, state: dict[str, Any]) -> dict[str, Any]:
        """Override to set model per intent before processing."""
        intent = state.get("intent", "balance_check")
        self.default_llm = self._select_model(intent)
        return await super().handle(state)

    async def _dispatch_tool(
        self, intent: str, state: dict[str, Any],
    ) -> dict[str, Any]:
        """Route to the right GraphQL operation based on intent."""
        phone = state.get("customer_context", {}).get(
            "phone_number", "+2348012345678",
        )

        if intent == "balance_check":
            return await self._call_tool(
                BALANCE_QUERY, {"phoneNumber": phone},
            )

        if intent == "transaction_history":
            # First get account ID from balance query
            acct_result = await self._call_tool(
                BALANCE_QUERY, {"phoneNumber": phone},
            )
            acct_data = acct_result.get("data", {}).get("accountBalance")
            if acct_data:
                account_id = acct_data["id"]
                return await self._call_tool(
                    TRANSACTION_QUERY,
                    {"accountId": account_id, "last": 10},
                )
            return acct_result

        if intent == "payment":
            return await self._handle_payment(state, phone)

        if intent == "dispute":
            return await self._handle_dispute(state, phone)

        return {"data": {}}

    async def _handle_payment(
        self, state: dict[str, Any], phone: str,
    ) -> dict[str, Any]:
        """Process payment — requires explicit 'yes' confirmation.

        First call returns requires_confirmation=true.
        Only processes when user has confirmed.
        """
        context = state.get("customer_context", {})
        amount = context.get("amount", 0.0)
        merchant = context.get("merchant", "unknown")
        confirmed = context.get("confirmed", False)

        if not confirmed:
            # Return confirmation request without calling the mutation
            logger.info(
                "billing.payment_needs_confirmation",
                phone=phone,
                amount=amount,
                merchant=merchant,
            )
            return {
                "data": {
                    "processPayment": {
                        "success": True,
                        "message": f"Payment of {amount} NGN to {merchant} requires confirmation.",
                        "referenceId": None,
                        "requiresConfirmation": True,
                    },
                },
                "_amount": amount,
                "_merchant": merchant,
            }

        # User confirmed — execute the payment
        result = await self._call_tool(
            PAYMENT_MUTATION,
            {"phoneNumber": phone, "amount": float(amount), "merchant": merchant},
        )
        result["_amount"] = amount
        result["_merchant"] = merchant
        return result

    async def _handle_dispute(
        self, state: dict[str, Any], phone: str,
    ) -> dict[str, Any]:
        """Handle dispute — always escalates to a ticket."""
        messages = state.get("messages", [])
        issue = ""
        for msg in reversed(messages):
            role = msg.role if hasattr(msg, "role") else msg.get("role", "")
            content = msg.content if hasattr(msg, "content") else msg.get("content", "")
            if role == "user":
                issue = content
                break

        result = await self._call_tool(
            ESCALATION_MUTATION,
            {"phoneNumber": phone, "issue": issue or "Dispute reported by customer"},
        )
        return result
