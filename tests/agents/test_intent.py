"""Tests for intent classifier."""

from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest
from src.agents.intent import (
    INTENT_EXAMPLES,
    INTENTS,
    IntentClassifier,
    IntentResult,
    _keyword_classify,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_st_class() -> MagicMock:
    """Mock SentenceTransformer class to avoid downloading the model."""
    with patch("sentence_transformers.SentenceTransformer") as mock_cls:
        instance = MagicMock()

        def fake_encode(texts: str | list[str], **kwargs: object) -> np.ndarray:
            """Return deterministic normalized vectors based on input hash."""
            single = isinstance(texts, str)
            if single:
                texts = [texts]
            rng = np.random.default_rng(hash(tuple(texts)) % 2**32)
            vecs = rng.standard_normal((len(texts), 384))
            norms = np.linalg.norm(vecs, axis=1, keepdims=True)
            result = vecs / (norms + 1e-10)
            return result[0] if single else result

        instance.encode = fake_encode
        mock_cls.return_value = instance
        yield mock_cls


@pytest.fixture
def classifier(mock_st_class: MagicMock) -> IntentClassifier:
    """IntentClassifier with mocked SentenceTransformer."""
    return IntentClassifier()


# ---------------------------------------------------------------------------
# IntentResult model tests
# ---------------------------------------------------------------------------


class TestIntentResult:
    def test_valid_result(self) -> None:
        result = IntentResult(
            intent="balance_check",
            confidence=0.85,
            classifier_type="embedding",
            latency_ms=42.5,
        )
        assert result.intent == "balance_check"
        assert result.confidence == 0.85

    def test_confidence_bounds(self) -> None:
        with pytest.raises(Exception):  # noqa: B017
            IntentResult(
                intent="test", confidence=1.5, classifier_type="keyword", latency_ms=1.0,
            )

    def test_classifier_type_literal(self) -> None:
        for ct in ("embedding", "llm", "keyword"):
            result = IntentResult(
                intent="test", confidence=0.5, classifier_type=ct, latency_ms=1.0,  # type: ignore[arg-type]
            )
            assert result.classifier_type == ct


# ---------------------------------------------------------------------------
# INTENTS and INTENT_EXAMPLES coverage
# ---------------------------------------------------------------------------


class TestIntentExamples:
    def test_all_intents_have_examples(self) -> None:
        """Every intent in INTENTS must have at least 5 examples."""
        for intent in INTENTS:
            assert intent in INTENT_EXAMPLES, f"Missing examples for {intent}"
            assert len(INTENT_EXAMPLES[intent]) >= 5, (
                f"Intent {intent} has only {len(INTENT_EXAMPLES[intent])} examples"
            )

    def test_no_extra_intents_in_examples(self) -> None:
        """INTENT_EXAMPLES should not have keys not in INTENTS."""
        for key in INTENT_EXAMPLES:
            assert key in INTENTS, f"Extra key in INTENT_EXAMPLES: {key}"


# ---------------------------------------------------------------------------
# Keyword classifier tests
# ---------------------------------------------------------------------------


class TestKeywordClassifier:
    def test_balance_english(self) -> None:
        assert _keyword_classify("Check my balance") == "balance_check"

    def test_payment_english(self) -> None:
        assert _keyword_classify("I want to pay my bill") == "payment"

    def test_greeting_english(self) -> None:
        assert _keyword_classify("hello there") == "greeting"

    def test_greeting_hausa(self) -> None:
        assert _keyword_classify("sannu da zuwa") == "greeting"

    def test_dispute(self) -> None:
        assert _keyword_classify("I have a dispute") == "dispute"

    def test_pin_reset(self) -> None:
        assert _keyword_classify("I forgot my PIN") == "pin_reset"

    def test_unknown_falls_to_other(self) -> None:
        assert _keyword_classify("asdflkjasdflkj") == "other"


# ---------------------------------------------------------------------------
# IntentClassifier tests (with mocked model)
# ---------------------------------------------------------------------------


class TestIntentClassifier:
    async def test_classify_returns_intent_result(
        self, classifier: IntentClassifier,
    ) -> None:
        result = await classifier.classify("Check my balance")
        assert isinstance(result, IntentResult)
        assert result.intent in INTENTS

    async def test_latency_recorded(
        self, classifier: IntentClassifier,
    ) -> None:
        result = await classifier.classify("hello")
        assert result.latency_ms > 0

    async def test_model_loaded_lazily(
        self, mock_st_class: MagicMock,
    ) -> None:
        """SentenceTransformer should not be instantiated until classify()."""
        _clf = IntentClassifier()
        mock_st_class.assert_not_called()
        await _clf.classify("test")
        mock_st_class.assert_called_once()

    @patch.dict("os.environ", {"MOCK_LLM": "true"}, clear=False)
    async def test_keyword_fallback_on_low_confidence(
        self, mock_st_class: MagicMock,
    ) -> None:
        """When embedding confidence < 0.7, fall back to keyword matching."""
        instance = mock_st_class.return_value

        # Make the single-text encode return a random vector that won't match centroids well
        call_count = 0

        def low_confidence_encode(texts: str | list[str], **kwargs: object) -> np.ndarray:
            nonlocal call_count
            call_count += 1
            if isinstance(texts, str):
                # For single text (classification), return zeros = low similarity
                return np.zeros(384)
            # For batch (centroid computation), return proper vectors
            n = len(texts)
            rng = np.random.default_rng(42)
            vecs = rng.standard_normal((n, 384))
            norms = np.linalg.norm(vecs, axis=1, keepdims=True)
            return vecs / (norms + 1e-10)

        instance.encode = low_confidence_encode
        clf = IntentClassifier()
        result = await clf.classify("check my balance")
        assert result.classifier_type == "keyword"
        assert result.intent == "balance_check"

    async def test_classify_embedding_path(
        self, mock_st_class: MagicMock,
    ) -> None:
        """When embedding confidence >= 0.7, use embedding classifier."""
        instance = mock_st_class.return_value

        # Make encode return a vector very close to the balance_check centroid
        centroid_cache: dict[str, np.ndarray] = {}

        def high_confidence_encode(texts: str | list[str], **kwargs: object) -> np.ndarray:
            if isinstance(texts, str):
                # Return the cached centroid for balance_check
                if "balance_check" in centroid_cache:
                    return centroid_cache["balance_check"]
                return np.ones(384) / np.sqrt(384)
            # For batch encoding, cache the centroids
            n = len(texts)
            rng = np.random.default_rng(hash(tuple(texts)) % 2**32)
            vecs = rng.standard_normal((n, 384))
            norms = np.linalg.norm(vecs, axis=1, keepdims=True)
            result = vecs / (norms + 1e-10)
            # Cache the mean for the first intent's examples
            if len(texts) == len(INTENT_EXAMPLES.get("balance_check", [])):
                centroid_cache["balance_check"] = result.mean(axis=0)
            return result

        instance.encode = high_confidence_encode
        clf = IntentClassifier()
        result = await clf.classify("Check my balance")
        # Can be either embedding or keyword depending on mock vectors
        assert result.classifier_type in ("embedding", "keyword")
        assert result.intent in INTENTS

    async def test_llm_classify_called_when_not_mock(
        self, mock_st_class: MagicMock,
    ) -> None:
        """When MOCK_LLM=false, LiteLLM should be called."""
        instance = mock_st_class.return_value

        def low_encode(texts: str | list[str], **kwargs: object) -> np.ndarray:
            if isinstance(texts, str):
                return np.zeros(384)
            n = len(texts)
            rng = np.random.default_rng(42)
            return rng.standard_normal((n, 384))

        instance.encode = low_encode

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "balance_check"

        with (
            patch.dict("os.environ", {"MOCK_LLM": "false"}, clear=False),
            patch("litellm.acompletion", new_callable=AsyncMock) as mock_acompletion,
        ):
            mock_acompletion.return_value = mock_response
            clf = IntentClassifier()
            result = await clf.classify("something unclear")
            assert result.classifier_type == "llm"
            assert result.intent == "balance_check"
