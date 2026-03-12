"""Cost-based LLM model selection."""

from src.config import LLMSettings

SIMPLE_INTENTS: frozenset[str] = frozenset({
    "balance_check",
    "greeting",
    "account_info",
    "transaction_history",
    "plan_change",
    "pin_reset",
    "other",
})

COMPLEX_INTENTS: frozenset[str] = frozenset({
    "dispute",
    "technical_issue",
})


def select_model(intent: str) -> str:
    """Select the LLM model based on intent complexity.

    Simple intents → gemini-flash (cheaper, faster).
    Complex intents → gpt-4o (more capable).
    """
    settings = LLMSettings(_env_file=None)
    if intent in COMPLEX_INTENTS:
        return settings.complex_model
    return settings.default_model
