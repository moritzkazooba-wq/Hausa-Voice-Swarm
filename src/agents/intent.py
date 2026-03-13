"""Intent classifier using paraphrase-multilingual-MiniLM-L12-v2.

Classifies Hausa (with English code-switching) utterances into one of the
supported intents via cosine similarity against pre-embedded exemplars.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Literal

import numpy as np
import structlog
from pydantic import BaseModel

from src.config.settings import AppSettings
from src.metrics.definitions import intent_classification_total

if TYPE_CHECKING:
    from numpy.typing import NDArray
    from sentence_transformers import SentenceTransformer

logger = structlog.get_logger()

# Supported intents
INTENTS = ("balance", "transfer", "bills", "general")

IntentLabel = Literal["balance", "transfer", "bills", "general"]

# Exemplar utterances per intent (Hausa + English code-switching)
_EXEMPLARS: dict[str, list[str]] = {
    "balance": [
        "Ina so in duba balance dina",
        "Nawa ne a asusuna?",
        "Check my balance",
        "How much do I have?",
        "Nawa ne kudin da ke cikin account dina",
        "What is my account balance",
        "balance",
    ],
    "transfer": [
        "Ina so in aika kudi",
        "Transfer money",
        "Send money to my friend",
        "Aika kudi zuwa",
        "Ina so in tura kudi",
        "I want to transfer funds",
        "transfer",
    ],
    "bills": [
        "Ina so in biya kuɗi",
        "Pay my bills",
        "Biya wutar lantarki",
        "Pay electricity",
        "Ina so in biya DSTV",
        "I want to pay a bill",
        "bills",
    ],
    "general": [
        "Taimako",
        "Help me",
        "I need help",
        "What can you do?",
        "Yaya zan yi",
        "I have a question",
        "general",
    ],
}

# Lazy singletons for model and embeddings
_model: SentenceTransformer | None = None
_exemplar_embeddings: dict[str, NDArray[np.float32]] | None = None

# Minimum similarity threshold — below this we fall back to "general"
_SIMILARITY_THRESHOLD = 0.3


def _get_model() -> SentenceTransformer:
    """Load the sentence-transformers model (lazy singleton)."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    return _model


def _get_exemplar_embeddings() -> dict[str, NDArray[np.float32]]:
    """Pre-compute and cache exemplar embeddings per intent."""
    global _exemplar_embeddings
    if _exemplar_embeddings is None:
        model = _get_model()
        _exemplar_embeddings = {}
        for intent, utterances in _EXEMPLARS.items():
            embeddings: NDArray[np.float32] = model.encode(
                utterances,
                convert_to_numpy=True,
            )
            _exemplar_embeddings[intent] = embeddings
    return _exemplar_embeddings


def _cosine_similarity(a: NDArray[np.float32], b: NDArray[np.float32]) -> NDArray[np.float32]:
    """Compute cosine similarity between vector ``a`` and matrix ``b``."""
    a_norm = a / (np.linalg.norm(a) + 1e-10)
    b_norm = b / (np.linalg.norm(b, axis=1, keepdims=True) + 1e-10)
    result: NDArray[np.float32] = np.dot(b_norm, a_norm)
    return result


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

    When ``MOCK_LLM=true`` (default), returns a mock result for fast testing.
    When ``MOCK_LLM=false``, loads the real sentence-transformers model and
    computes cosine similarity against intent exemplar embeddings.
    """
    start = time.monotonic()

    settings = AppSettings()
    if settings.mock_llm:
        # Mock classification — fast path for development / CI
        intent: IntentLabel = "general"
        confidence = 0.85
    else:
        # Real classification via sentence-transformers
        try:
            model = _get_model()
            exemplar_embs = _get_exemplar_embeddings()
        except Exception:
            # Model not available (no network, disk, etc.) — fall back to mock
            await logger.awarn("intent_classifier_model_unavailable", utterance=utterance)
            intent = "general"
            confidence = 0.5
        else:
            query_embedding: NDArray[np.float32] = model.encode(
                utterance,
                convert_to_numpy=True,
            )

            best_intent: IntentLabel = "general"
            best_score: float = 0.0

            for intent_name, embs in exemplar_embs.items():
                similarities = _cosine_similarity(query_embedding, embs)
                max_sim = float(np.max(similarities))
                if max_sim > best_score:
                    best_score = max_sim
                    best_intent = intent_name  # type: ignore[assignment]

            intent = best_intent if best_score >= _SIMILARITY_THRESHOLD else "general"
            confidence = best_score

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
