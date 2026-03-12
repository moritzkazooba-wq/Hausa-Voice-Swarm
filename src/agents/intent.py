"""Intent classifier using keyword matching (with sentence-transformers upgrade path)."""

from __future__ import annotations

from dataclasses import dataclass

# Intent definitions with keyword patterns supporting Hausa + English code-switching
INTENT_KEYWORDS: dict[str, list[str]] = {
    "check_balance": [
        "balance", "how much", "nawa", "kudin", "kudi", "account",
        "nawa ne", "nawa kudi", "check balance", "my balance",
    ],
    "transfer_money": [
        "transfer", "send money", "aika kudi", "aika", "tura kudi",
        "send", "tura", "pay someone",
    ],
    "pay_bill": [
        "bill", "pay bill", "biya", "dstv", "gotv", "airtime",
        "electricity", "nepa", "recharge", "top up", "subscribe",
    ],
    "pin_reset": [
        "pin", "reset pin", "change pin", "forgot pin", "password",
        "canza pin", "manta pin",
    ],
    "technical_issue": [
        "network", "error", "problem", "not working", "slow",
        "failed", "issue", "matsala", "broken", "can't send",
        "wahala", "ba ya aiki", "hang", "crash", "timeout",
    ],
    "speak_to_human": [
        "agent", "human", "person", "speak to someone", "operator",
        "help me", "taimaka", "mutum", "representative", "escalate",
        "talk to someone",
    ],
    "greeting": [
        "hello", "hi", "sannu", "barka", "good morning", "good afternoon",
        "ina kwana", "ina wuni", "hey", "salama",
    ],
    "goodbye": [
        "bye", "goodbye", "sai anjima", "sai an jima", "thank",
        "thanks", "nagode", "na gode", "sai watarana",
    ],
    "general": [],  # Fallback intent
}


@dataclass
class IntentResult:
    """Result of intent classification."""

    intent: str
    confidence: float
    top_intents: list[tuple[str, float]]


def classify_intent(text: str) -> IntentResult:
    """Classify user text into an intent using keyword matching.

    Returns the best-matching intent with a confidence score.
    For production, replace with sentence-transformers cosine similarity.
    """
    text_lower = text.lower().strip()
    scores: dict[str, float] = {}

    for intent, keywords in INTENT_KEYWORDS.items():
        if not keywords:
            continue
        matches = sum(1 for kw in keywords if kw in text_lower)
        if matches > 0:
            scores[intent] = matches / len(keywords)

    if not scores:
        return IntentResult(
            intent="general",
            confidence=0.3,
            top_intents=[("general", 0.3)],
        )

    sorted_intents = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    best_intent, best_score = sorted_intents[0]

    # Normalize confidence to 0-1 range (cap at 1.0)
    confidence = min(best_score * 3.0, 1.0)

    top_intents = [(intent, min(score * 3.0, 1.0)) for intent, score in sorted_intents[:3]]

    return IntentResult(
        intent=best_intent,
        confidence=confidence,
        top_intents=top_intents,
    )
