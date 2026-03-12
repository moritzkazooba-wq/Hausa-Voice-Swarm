"""Intent classifier using paraphrase-multilingual-MiniLM-L12-v2.

Classifies Hausa (with English code-switching) utterances into one of the
supported intents via cosine similarity against pre-embedded exemplars.
"""

from __future__ import annotations

import time
from typing import Literal

import structlog
from pydantic import BaseModel

from src.metrics.definitions import intent_classification_total

logger = structlog.get_logger()

# Supported intents
INTENTS = ("balance", "transfer", "bills", "general")

IntentLabel = Literal["balance", "transfer", "bills", "general"]


class ClassificationResult(BaseModel):
    """Result from the intent classifier."""

    intent: IntentLabel
    confidence: float
    utterance: str
    classifier_type: str
    elapsed_ms: float


async def classify_intent(
    utterance: str,
    *,
    classifier_type: str = "sentence-transformers",
) -> ClassificationResult:
    """Classify an utterance into a domain intent.

    Currently returns a mock result. When real model is loaded, will compute
    cosine similarity against intent exemplar embeddings.
    """
    start = time.monotonic()

    # Mock classification — default to "general" with moderate confidence.
    # Real implementation will load paraphrase-multilingual-MiniLM-L12-v2
    # and compute cosine similarity against intent embeddings.
    intent: IntentLabel = "general"
    confidence = 0.85

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
