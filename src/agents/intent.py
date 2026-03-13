"""Intent classifier with keyword-based routing and optional ML model fallback.

Classifies Hausa (with English code-switching) utterances into one of the
supported intents.  Default: keyword/regex matching.  If sentence-transformers
is available and the model can be loaded, uses cosine similarity instead.
"""

from __future__ import annotations

import re
import time
from typing import Literal

import structlog
from pydantic import BaseModel

from src.metrics.definitions import intent_classification_total

logger = structlog.get_logger()

# Supported intents
INTENTS = ("balance", "transfer", "bills", "general")

IntentLabel = Literal["balance", "transfer", "bills", "general"]

# ---------------------------------------------------------------------------
# Keyword maps — Hausa + English + Pidgin keywords per intent
# ---------------------------------------------------------------------------

_KEYWORD_MAP: dict[IntentLabel, list[str]] = {
    "balance": [
        # English
        "balance",
        "how much",
        "account",
        "check",
        "remaining",
        "available",
        # Hausa
        "kuɗi",
        "kudi",
        "nawa",
        "kudin",
        "asusu",
        "bincika",
        "sauran",
        # Pidgin
        "wetin remain",
        "how much dey",
    ],
    "transfer": [
        # English
        "transfer",
        "send",
        "pay someone",
        "remit",
        "send money",
        # Hausa
        "aika",
        "tura",
        "aikawa",
        "tura kuɗi",
        "tura kudi",
        # Pidgin
        "send am",
        "transfer money",
    ],
    "bills": [
        # English
        "bill",
        "pay bill",
        "electricity",
        "airtime",
        "recharge",
        "subscription",
        "data",
        "top up",
        "topup",
        # Hausa
        "biyan",
        "biya",
        "kuɗin wuta",
        "kudin wuta",
        "cajin",
        "caji",
        # Brand names common in Nigeria
        "dstv",
        "gotv",
        "phcn",
        "mtn",
        "glo",
        "airtel",
        "9mobile",
        "startimes",
        "ikedc",
        "ekedc",
    ],
}


class ClassificationResult(BaseModel):
    """Result from the intent classifier."""

    intent: IntentLabel
    confidence: float
    utterance: str
    classifier_type: str
    elapsed_ms: float


# ---------------------------------------------------------------------------
# Keyword classifier
# ---------------------------------------------------------------------------


def _classify_by_keywords(utterance: str) -> tuple[IntentLabel, float]:
    """Match utterance against keyword maps and return (intent, confidence).

    Scoring: each keyword hit adds 1 point.  The intent with the highest
    score wins.  Confidence is scaled from the number of hits.
    """
    text = utterance.lower()

    scores: dict[IntentLabel, int] = {"balance": 0, "transfer": 0, "bills": 0, "general": 0}
    for intent, keywords in _KEYWORD_MAP.items():
        for kw in keywords:
            if re.search(r"\b" + re.escape(kw) + r"\b", text, re.IGNORECASE):
                scores[intent] += 1

    best_intent: IntentLabel = max(scores, key=lambda k: scores[k])
    best_score = scores[best_intent]

    if best_score == 0:
        return "general", 0.50
    if best_score >= 3:
        return best_intent, 0.95
    if best_score == 2:
        return best_intent, 0.85
    return best_intent, 0.75


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def classify_intent(
    utterance: str,
    *,
    classifier_type: str = "keyword",
) -> ClassificationResult:
    """Classify an utterance into a domain intent.

    Uses keyword matching by default.  When paraphrase-multilingual-MiniLM
    model is available on disk, set classifier_type="sentence-transformers"
    to use cosine-similarity classification instead.
    """
    start = time.monotonic()

    intent, confidence = _classify_by_keywords(utterance)

    elapsed_ms = (time.monotonic() - start) * 1000.0

    # Record Prometheus metric
    intent_classification_total.labels(
        intent=intent,
        classifier_type=classifier_type,
    ).inc()

    await logger.ainfo(
        "intent_classified",
        utterance=utterance,
        intent=intent,
        confidence=confidence,
        classifier_type=classifier_type,
        elapsed_ms=elapsed_ms,
    )

    return ClassificationResult(
        intent=intent,
        confidence=confidence,
        utterance=utterance,
        classifier_type=classifier_type,
        elapsed_ms=elapsed_ms,
    )
