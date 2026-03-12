"""Account agent: pin_reset, plan_change, account_info."""

import secrets
from typing import Any, ClassVar

import structlog

from src.agents.domains.base import DomainAgent

logger = structlog.get_logger()

# GraphQL operations
ACCOUNT_QUERY = """
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

PIN_RESET_MUTATION = """
mutation ResetPin($phoneNumber: String!) {
    resetPin(phoneNumber: $phoneNumber) {
        success
        message
        referenceId
        requiresConfirmation
    }
}
"""

PLAN_CHANGE_MUTATION = """
mutation ChangePlan($phoneNumber: String!, $newPlan: String!) {
    changePlan(phoneNumber: $phoneNumber, newPlan: $newPlan) {
        success
        message
        referenceId
        requiresConfirmation
    }
}
"""


class AccountAgent(DomainAgent):
    """Handles PIN reset, plan changes, and account info queries.

    All operations use gemini-flash (simple intents).
    PIN reset: requires confirmation + mock verification code.
    Plan change: requires confirmation.
    """

    name = "account_agent"
    description = "Handles PIN reset, plan changes, and account info"
    handled_intents: ClassVar[list[str]] = ["pin_reset", "plan_change", "account_info"]
    available_tools: ClassVar[list[str]] = ["accountBalance", "resetPin", "changePlan"]
    default_llm = "gemini-flash"

    async def _dispatch_tool(
        self, intent: str, state: dict[str, Any],
    ) -> dict[str, Any]:
        """Route to the right GraphQL operation based on intent."""
        phone = state.get("customer_context", {}).get(
            "phone_number", "+2348012345678",
        )

        if intent == "account_info":
            return await self._call_tool(
                ACCOUNT_QUERY, {"phoneNumber": phone},
            )

        if intent == "pin_reset":
            return await self._handle_pin_reset(state, phone)

        if intent == "plan_change":
            return await self._handle_plan_change(state, phone)

        return {"data": {}}

    async def _handle_pin_reset(
        self, state: dict[str, Any], phone: str,
    ) -> dict[str, Any]:
        """Handle PIN reset — requires confirmation + sends mock verification code.

        First call returns requiresConfirmation=true.
        After confirmation, generates a mock verification code.
        """
        context = state.get("customer_context", {})
        confirmed = context.get("confirmed", False)

        if not confirmed:
            logger.info("account.pin_reset_needs_confirmation", phone=phone)
            return {
                "data": {
                    "resetPin": {
                        "success": True,
                        "message": (
                            "PIN reset requires confirmation."
                            " A verification code will be sent."
                        ),
                        "referenceId": None,
                        "requiresConfirmation": True,
                    },
                },
            }

        # User confirmed — execute PIN reset and generate verification code
        result = await self._call_tool(
            PIN_RESET_MUTATION, {"phoneNumber": phone},
        )

        # Generate a mock 6-digit verification code
        verification_code = f"{secrets.randbelow(900000) + 100000}"
        logger.info(
            "account.pin_reset_code_sent",
            phone=phone,
            code=verification_code,
        )

        # Attach verification code to result for response generation
        result["_verification_code"] = verification_code
        return result

    async def _handle_plan_change(
        self, state: dict[str, Any], phone: str,
    ) -> dict[str, Any]:
        """Handle plan change — requires confirmation."""
        context = state.get("customer_context", {})
        new_plan = context.get("new_plan", "basic")
        confirmed = context.get("confirmed", False)

        if not confirmed:
            logger.info(
                "account.plan_change_needs_confirmation",
                phone=phone,
                new_plan=new_plan,
            )
            return {
                "data": {
                    "changePlan": {
                        "success": True,
                        "message": f"Plan change to {new_plan} requires confirmation.",
                        "referenceId": None,
                        "requiresConfirmation": True,
                    },
                },
                "_plan": new_plan,
            }

        # User confirmed — execute plan change
        result = await self._call_tool(
            PLAN_CHANGE_MUTATION,
            {"phoneNumber": phone, "newPlan": new_plan},
        )
        result["_plan"] = new_plan
        return result
