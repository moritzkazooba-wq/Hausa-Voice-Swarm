"""Intent classifier: embedding fast path + LLM/keyword fallback."""

import asyncio
import time
from typing import Any, Literal

import numpy as np
import structlog
from numpy.typing import NDArray
from pydantic import BaseModel, Field

from src.config import AppSettings, LLMSettings

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

INTENTS: list[str] = [
    "balance_check",
    "transaction_history",
    "payment",
    "dispute",
    "pin_reset",
    "plan_change",
    "account_info",
    "technical_issue",
    "speak_to_human",
    "greeting",
    "other",
]

INTENT_EXAMPLES: dict[str, list[str]] = {
    "balance_check": [
        # Hausa
        "Ina so in duba kuɗina",
        "Nawa ne a asusuna?",
        "Duba ma kuɗi",
        "Yaya kuɗina?",
        "Ina so in san kuɗi na",
        "Nawa ne kuɗi na a yanzu?",
        # English
        "Check my balance",
        "How much is in my account?",
        "What's my balance?",
        "Show me my balance",
        "I want to know my balance",
        # Pidgin
        "Wetin dey my account?",
        "How much I get?",
    ],
    "transaction_history": [
        # Hausa
        "Nuna min ma'amalar da na yi",
        "Ina so in ga tarihin ma'amala",
        "Wane ne ma'amala na baya-bayan nan?",
        "Nuna min abin da ya faru a asusuna",
        "Wane kudade suka shiga asusuna?",
        # English
        "Show me my transactions",
        "What are my recent transactions?",
        "Transaction history please",
        "Show my last payments",
        "I want to see my transaction list",
        # Pidgin
        "Show me wetin happen for my account",
        "Wetin I don pay?",
    ],
    "payment": [
        # Hausa
        "Ina so in biya",
        "Biya kuɗi zuwa",
        "Aika kuɗi",
        "Ina so in tura kuɗi",
        "Biya lissafin waya na",
        # English
        "I want to make a payment",
        "Pay my bill",
        "Send money to someone",
        "I need to pay for something",
        "Make a transfer",
        # Pidgin
        "I wan pay money",
        "Send money give am",
    ],
    "dispute": [
        # Hausa
        "Akwai matsala da ma'amala",
        "Ba na yarda da wannan cajin",
        "An yi min caji ba daidai ba",
        "Ina neman dawo da kuɗina",
        "Akwai kuskure a lissafina",
        # English
        "I have a dispute about a transaction",
        "There's a wrong charge on my account",
        "I want to dispute a payment",
        "I was charged incorrectly",
        "I need a refund for a wrong transaction",
        # Pidgin
        "Dem charge me wrong money",
        "I no agree with this charge",
    ],
    "pin_reset": [
        # Hausa
        "Ina so in sake saita lambar sirrina",
        "Na manta da PIN na",
        "Canja lambar sirrina",
        "Taimaka min in sake saita PIN",
        "Ba zan iya tuna da PIN na ba",
        # English
        "I forgot my PIN",
        "I need to reset my PIN",
        "Change my PIN please",
        "Help me reset my password",
        "I can't remember my PIN",
        # Pidgin
        "I forget my PIN",
        "Change my PIN for me",
    ],
    "plan_change": [
        # Hausa
        "Ina so in canja shirin na",
        "Canja tsarin kuɗi na",
        "Ina so in haura shirin na",
        "Ina so in rage shirin na",
        "Wane shirye-shirye kuke da su?",
        # English
        "I want to change my plan",
        "Upgrade my plan",
        "Downgrade my plan please",
        "What plans are available?",
        "Switch my subscription",
        # Pidgin
        "I wan change my plan",
        "Upgrade my plan abeg",
    ],
    "account_info": [
        # Hausa
        "Ina so in san bayanan asusuna",
        "Nuna min bayanan asusuna",
        "Menene sunan asusuna?",
        "Wane irin shirin nake?",
        "Bayar da bayanan asusuna",
        # English
        "Show me my account details",
        "What plan am I on?",
        "I need my account information",
        "What's my phone number on file?",
        "Tell me about my account",
        # Pidgin
        "Show me my account info",
        "Wetin be my account details?",
    ],
    "technical_issue": [
        # Hausa
        "Hanyar sadarwa ba ta aiki",
        "Ba zan iya shiga asusuna ba",
        "Akwai matsalar fasaha",
        "Manhaja ba ta aiki",
        "Ina samun kuskure",
        # English
        "The network is not working",
        "I can't access my account",
        "There's a technical problem",
        "The app is not working",
        "I'm getting an error",
        # Pidgin
        "Network no dey work",
        "I no fit enter my account",
    ],
    "speak_to_human": [
        # Hausa
        "Ina so in yi magana da mutum",
        "Ka haɗa ni da wakili",
        "Zan so in yi magana da wani",
        "Ba na son bot",
        "Ina bukatar taimakon mutum",
        # English
        "I want to speak to a human",
        "Connect me to an agent",
        "Transfer me to a person",
        "I don't want to talk to a bot",
        "Let me talk to someone real",
        # Pidgin
        "I wan talk to person",
        "Give me real person",
    ],
    "greeting": [
        # Hausa
        "Sannu",
        "Sannu da zuwa",
        "Barka da kwana",
        "Yaya dai?",
        "Ina kwana?",
        "Salama alaikum",
        # English
        "Hello",
        "Hi",
        "Good morning",
        "Hey there",
        "Good afternoon",
        # Pidgin
        "How far?",
        "How you dey?",
    ],
    "other": [
        # Hausa
        "Ba na da tambaya",
        "Komai ya yi kyau",
        "Na gode",
        "Sai anjima",
        "Ban gane ba",
        # English
        "I don't have a question",
        "Everything is fine",
        "Thank you",
        "Goodbye",
        "I don't understand",
        # Pidgin
        "No wahala",
        "Thank you o",
    ],
}

# Keyword map for mock/fallback classification
KEYWORD_MAP: dict[str, list[str]] = {
    "balance_check": ["balance", "kuɗi", "kudina", "nawa", "how much", "duba"],
    "transaction_history": [
        "transaction", "history", "ma'amala", "tarihi", "recent", "payments",
    ],
    "payment": ["pay", "biya", "send", "transfer", "aika", "tura"],
    "dispute": ["dispute", "wrong", "charge", "refund", "kuskure", "matsala"],
    "pin_reset": ["pin", "reset", "forgot", "password", "manta", "sirri"],
    "plan_change": ["plan", "upgrade", "downgrade", "switch", "canja", "shiri"],
    "account_info": ["account info", "details", "asusu", "bayani"],
    "technical_issue": ["error", "network", "broken", "crash", "hanyar", "fasaha"],
    "speak_to_human": ["human", "person", "agent", "mutum", "wakili", "real"],
    "greeting": ["hello", "hi", "sannu", "barka", "salama", "hey", "how far"],
    "other": [],
}


# ---------------------------------------------------------------------------
# IntentResult model
# ---------------------------------------------------------------------------


class IntentResult(BaseModel):
    """Result of intent classification."""

    intent: str
    confidence: float = Field(ge=0.0, le=1.0)
    classifier_type: Literal["embedding", "llm", "keyword"]
    latency_ms: float


# ---------------------------------------------------------------------------
# IntentClassifier
# ---------------------------------------------------------------------------


class IntentClassifier:
    """Embedding-based intent classifier with LLM/keyword fallback."""

    MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
    CONFIDENCE_THRESHOLD = 0.7

    def __init__(self) -> None:
        self._model: Any = None  # SentenceTransformer (lazy loaded)
        self._centroids: dict[str, NDArray[np.float64]] = {}
        self._ready = False

    async def _ensure_model(self) -> None:
        """Lazy-load the model and precompute centroids."""
        if self._ready:
            return
        from sentence_transformers import SentenceTransformer

        logger.info("intent.loading_model", model=self.MODEL_NAME)
        self._model = await asyncio.to_thread(SentenceTransformer, self.MODEL_NAME)
        self._compute_centroids()
        self._ready = True
        logger.info("intent.model_ready", n_intents=len(self._centroids))

    def _compute_centroids(self) -> None:
        """Pre-compute mean embedding per intent from examples."""
        for intent, examples in INTENT_EXAMPLES.items():
            embeddings: NDArray[np.float64] = self._model.encode(examples)
            self._centroids[intent] = embeddings.mean(axis=0)

    def _match_centroid(
        self, embedding: NDArray[np.float64],
    ) -> tuple[str, float]:
        """Find the closest intent centroid via cosine similarity."""
        best_intent = "other"
        best_score = 0.0
        emb_norm = embedding / (np.linalg.norm(embedding) + 1e-10)
        for intent, centroid in self._centroids.items():
            centroid_norm = centroid / (np.linalg.norm(centroid) + 1e-10)
            score = float(np.dot(emb_norm, centroid_norm))
            if score > best_score:
                best_score = score
                best_intent = intent
        return best_intent, best_score

    async def classify(self, text: str) -> IntentResult:
        """Classify user text into an intent.

        Fast path: embedding cosine similarity (< 100ms target).
        Slow path: keyword matching (MOCK_LLM=true) or LiteLLM call.
        """
        start = time.perf_counter()
        await self._ensure_model()

        # Encode the input text in a thread pool (sync CPU-bound work)
        embedding: NDArray[np.float64] = await asyncio.to_thread(
            self._model.encode, text,
        )
        best_intent, best_score = self._match_centroid(embedding)
        elapsed_ms = (time.perf_counter() - start) * 1000

        if best_score >= self.CONFIDENCE_THRESHOLD:
            logger.debug(
                "intent.classified",
                intent=best_intent,
                confidence=round(best_score, 3),
                classifier="embedding",
                latency_ms=round(elapsed_ms, 1),
            )
            return IntentResult(
                intent=best_intent,
                confidence=round(best_score, 4),
                classifier_type="embedding",
                latency_ms=round(elapsed_ms, 2),
            )

        # Fall back to slow path
        return await self._slow_classify(text, elapsed_ms)

    async def _slow_classify(
        self, text: str, latency_so_far: float,
    ) -> IntentResult:
        """Fallback classification when embedding confidence is low."""
        settings = AppSettings(_env_file=None)
        start = time.perf_counter()

        if settings.mock_llm:
            intent = _keyword_classify(text)
            elapsed = (time.perf_counter() - start) * 1000
            total_ms = latency_so_far + elapsed
            logger.debug(
                "intent.keyword_fallback",
                intent=intent,
                latency_ms=round(total_ms, 1),
            )
            return IntentResult(
                intent=intent,
                confidence=0.6,
                classifier_type="keyword",
                latency_ms=round(total_ms, 2),
            )

        # Real LLM classification via LiteLLM
        return await self._llm_classify(text, latency_so_far)

    async def _llm_classify(
        self, text: str, latency_so_far: float,
    ) -> IntentResult:
        """Classify via LiteLLM when embedding confidence is low."""
        import litellm

        llm_settings = LLMSettings(_env_file=None)
        start = time.perf_counter()

        prompt = (
            f"Classify the following customer message into exactly one of these intents: "
            f"{', '.join(INTENTS)}.\n\n"
            f'Message: "{text}"\n\n'
            f"Respond with only the intent name, nothing else."
        )

        response = await litellm.acompletion(
            model=llm_settings.default_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=20,
            temperature=0.0,
        )
        raw = response.choices[0].message.content.strip().lower()
        intent = raw if raw in INTENTS else "other"
        elapsed = (time.perf_counter() - start) * 1000
        total_ms = latency_so_far + elapsed

        logger.debug(
            "intent.llm_classified",
            intent=intent,
            raw=raw,
            latency_ms=round(total_ms, 1),
        )
        return IntentResult(
            intent=intent,
            confidence=0.75,
            classifier_type="llm",
            latency_ms=round(total_ms, 2),
        )


# ---------------------------------------------------------------------------
# Keyword-based fallback (used when MOCK_LLM=true)
# ---------------------------------------------------------------------------


def _keyword_classify(text: str) -> str:
    """Simple keyword matching for mock/fallback classification."""
    lower = text.lower()
    for intent, keywords in KEYWORD_MAP.items():
        for keyword in keywords:
            if keyword in lower:
                return intent
    return "other"
