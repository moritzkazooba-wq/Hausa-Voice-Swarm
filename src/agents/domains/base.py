"""Base class for domain agents with GraphQL tool calling and LLM response generation."""

from datetime import UTC, datetime
from typing import Any, ClassVar

import httpx
import structlog

from src.agents.base import BaseAgent
from src.config import AppSettings
from src.models.session import AgentMessage

logger = structlog.get_logger()

# Canned responses keyed by intent for MOCK_LLM=true mode
MOCK_RESPONSES: dict[str, dict[str, str]] = {
    "balance_check": {
        "ha": "Kuɗin ku ya kai {balance}. Akwai wani abin da kuke bukata?",
        "en": "Your balance is {balance}. Is there anything else you need?",
        "pcm": "Your balance na {balance}. You need anything else?",
    },
    "transaction_history": {
        "ha": "Ga ma'amalolin ku na baya-bayan nan. Akwai wani abu kuma?",
        "en": "Here are your recent transactions. Anything else?",
        "pcm": "See your recent transactions. Anything else?",
    },
    "payment": {
        "ha": "Za mu biya {amount} zuwa {merchant}. Shin kun tabbatar?",
        "en": "We will pay {amount} to {merchant}. Do you confirm?",
        "pcm": "We go pay {amount} to {merchant}. You confirm?",
    },
    "dispute": {
        "ha": "Mun karɓi ƙarar ku. Za mu bincika kuma mu amsa.",
        "en": "We've received your dispute. We'll investigate and respond.",
        "pcm": "We don receive your dispute. We go check am.",
    },
    "pin_reset": {
        "ha": "Za mu sake saita PIN ɗinku. Mun aika lambar tabbatarwa.",
        "en": "We'll reset your PIN. A verification code has been sent.",
        "pcm": "We go reset your PIN. We don send verification code.",
    },
    "plan_change": {
        "ha": "Za mu canja shirin ku zuwa {plan}. Shin kun tabbatar?",
        "en": "We'll change your plan to {plan}. Do you confirm?",
        "pcm": "We go change your plan to {plan}. You confirm?",
    },
    "account_info": {
        "ha": "Ga bayanan asusun ku. Akwai wani abu kuma?",
        "en": "Here are your account details. Anything else?",
        "pcm": "See your account details. Anything else?",
    },
}


class DomainAgent(BaseAgent):
    """Base class for domain agents that call GraphQL tools and generate responses.

    Subclasses must set:
        name: str — agent identifier
        description: str — what this agent handles
        handled_intents: list[str] — intents this agent processes
        available_tools: list[str] — GraphQL operation names this agent can call
        default_llm: str — LLM model name for response generation
    """

    name: str = ""
    description: str = ""
    handled_intents: ClassVar[list[str]] = []
    available_tools: ClassVar[list[str]] = []
    default_llm: str = "gemini-flash"

    async def handle(self, state: dict[str, Any]) -> dict[str, Any]:
        """Process the user request via tool call + response generation."""
        intent = state.get("intent", "other")
        lang = state.get("language", "en")
        phone = state.get("customer_context", {}).get("phone_number", "+2348012345678")

        tool_result = await self._dispatch_tool(intent, state)
        response = await self._generate_response(
            intent=intent,
            language=lang,
            tool_result=tool_result,
            phone_number=phone,
            state=state,
        )

        return {
            "current_agent": self.name,
            "response": response,
            "messages": [
                AgentMessage(
                    role="assistant",
                    content=response,
                    timestamp=datetime.now(UTC),
                    agent_name=self.name,
                ),
            ],
        }

    async def _dispatch_tool(
        self, intent: str, state: dict[str, Any],
    ) -> dict[str, Any]:
        """Dispatch to the appropriate GraphQL tool based on intent."""
        raise NotImplementedError

    async def _call_tool(
        self, operation: str, variables: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a GraphQL operation via httpx POST.

        Uses AppSettings.api_base_url — never hardcoded localhost.
        """
        settings = AppSettings(_env_file=None)
        url = f"{settings.api_base_url}/graphql"

        logger.debug(
            "domain_agent.call_tool",
            agent=self.name,
            operation_name=operation[:50],
            url=url,
        )

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                url,
                json={"query": operation, "variables": variables},
            )
            resp.raise_for_status()
            return resp.json()  # type: ignore[no-any-return]

    async def _generate_response(
        self,
        *,
        intent: str,
        language: str,
        tool_result: dict[str, Any],
        phone_number: str,
        state: dict[str, Any],
    ) -> str:
        """Generate a natural language response from tool results.

        MOCK_LLM=true: uses canned responses keyed by intent.
        MOCK_LLM=false: calls LiteLLM for natural response generation.
        """
        app_settings = AppSettings(_env_file=None)

        if app_settings.mock_llm:
            return self._mock_response(intent, language, tool_result)

        return await self._llm_response(intent, language, tool_result, phone_number)

    def _mock_response(
        self, intent: str, language: str, tool_result: dict[str, Any],
    ) -> str:
        """Return a canned response with template substitution."""
        intent_responses = MOCK_RESPONSES.get(intent, {})
        template = intent_responses.get(language, intent_responses.get("en", ""))
        if not template:
            return "Request processed successfully."

        # Extract values from tool_result for template substitution
        data = tool_result.get("data", {})
        fmt: dict[str, str] = {}

        # Balance from accountBalance query
        if data.get("accountBalance"):
            acct = data["accountBalance"]
            fmt["balance"] = f"N{acct.get('balance', '0')}"
            fmt["name"] = acct.get("name", "")

        # Payment mutation result
        if data.get("processPayment"):
            pay = data["processPayment"]
            fmt["reference"] = pay.get("referenceId", "")

        # Plan change
        if data.get("changePlan"):
            fmt["plan"] = tool_result.get("_plan", "new plan")

        # Generic extraction from variables
        fmt.setdefault("amount", str(tool_result.get("_amount", "")))
        fmt.setdefault("merchant", str(tool_result.get("_merchant", "")))
        fmt.setdefault("plan", str(tool_result.get("_plan", "")))

        try:
            return template.format(**fmt)
        except KeyError:
            return template

    async def _llm_response(
        self,
        intent: str,
        language: str,
        tool_result: dict[str, Any],
        phone_number: str,
    ) -> str:
        """Generate response via LiteLLM."""
        import litellm

        from src.agents.prompts import build_system_prompt

        lang_names = {"ha": "Hausa", "en": "English", "pcm": "Nigerian Pidgin"}
        lang_name = lang_names.get(language, "English")

        system_prompt = build_system_prompt(language, phone_number)
        user_prompt = (
            f"The customer's intent is '{intent}'. "
            f"Tool result: {tool_result}. "
            f"Respond in {lang_name} in maximum 2 sentences."
        )

        response = await litellm.acompletion(
            model=self.default_llm,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=150,
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()  # type: ignore[no-any-return]
