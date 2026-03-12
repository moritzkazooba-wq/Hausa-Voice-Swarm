"""System prompt templates for voice agents."""

LANGUAGE_NAMES: dict[str, str] = {
    "ha": "Hausa",
    "en": "English",
    "pcm": "Nigerian Pidgin",
}

SYSTEM_PROMPT_TEMPLATE = (
    "You are a helpful mobile money customer service agent. "
    "Customer: {customer_name}. Language: {language_name}. "
    "Respond in {language_name}. Maximum 2 sentences. Be clear and direct."
)


def build_system_prompt(language: str, customer_name: str) -> str:
    """Build a system prompt parameterized by language and customer name."""
    language_name = LANGUAGE_NAMES.get(language, "English")
    return SYSTEM_PROMPT_TEMPLATE.format(
        customer_name=customer_name,
        language_name=language_name,
    )
