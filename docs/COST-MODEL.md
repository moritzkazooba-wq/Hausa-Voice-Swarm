# Cost Model — Hausa Voice Swarm

> Target: **< $0.15 per interaction** at 10M+ monthly interactions.
>
> Pricing estimates as of March 2026 — verify current rates before publishing.

---

## Scale Assumptions

| Metric | Value |
|---|---|
| Monthly interactions | 10,000,000 |
| Daily interactions | ~333,000 |
| Peak hourly | 40,000–55,000 |
| Peak concurrent sessions | 700–900 |
| Voice share | 60% (6M voice / 4M text-only) |
| Avg voice duration | 2 minutes |
| LLM calls per interaction | 3 (intent + domain agent + confirmation/follow-up) |
| LLM routing | 70% Gemini Flash (simple) / 30% GPT-4o (complex) |
| Daily LLM calls | ~1M–1.5M |

---

## Unit Pricing (Estimated March 2026)

| Service | Unit | Price |
|---|---|---|
| GPT-4o | 1M input tokens | $2.50 |
| GPT-4o | 1M output tokens | $10.00 |
| Gemini 2.0 Flash | 1M input tokens | $0.075 |
| Gemini 2.0 Flash | 1M output tokens | $0.30 |
| Intron Hausa ASR | per minute | ~$0.006 |
| Cartesia TTS | 1K characters | ~$0.015 |
| GCP g2-standard-4 (GPU) | per hour | ~$0.70 |
| GCP Memorystore Redis 2GB | per GB/hour | ~$0.049 |
| CockroachDB Serverless | 1M Request Units | ~$1.00 |

---

## Per-Interaction Cost Breakdown

### 1. ASR (Voice Only — 60% of interactions)

- Avg duration: 2 minutes per voice interaction
- Cost: 2 min × $0.006/min = **$0.012 per voice interaction**
- Blended (60% voice): $0.012 × 0.60 = **$0.0072/interaction**

### 2. TTS (Voice Only — 60% of interactions)

- Avg response: ~150 characters per turn, ~3 turns = 450 characters
- Cost: 0.45 × $0.015 = **$0.00675 per voice interaction**
- Blended (60% voice): $0.00675 × 0.60 = **$0.00405/interaction**

### 3. LLM — Gemini Flash (70% of calls)

Per call assumptions: ~300 input tokens (system prompt + context), ~80 output tokens (short Hausa response).

| | Tokens/call | Calls/interaction | Cost |
|---|---|---|---|
| Input | 300 | 3 × 0.70 = 2.1 | 630 tokens × $0.075/1M = $0.0000473 |
| Output | 80 | 2.1 | 168 tokens × $0.30/1M = $0.0000504 |
| **Subtotal** | | | **$0.0000977/interaction** |

### 4. LLM — GPT-4o (30% of calls)

Per call assumptions: ~500 input tokens (longer context for complex queries), ~120 output tokens.

| | Tokens/call | Calls/interaction | Cost |
|---|---|---|---|
| Input | 500 | 3 × 0.30 = 0.9 | 450 tokens × $2.50/1M = $0.001125 |
| Output | 120 | 0.9 | 108 tokens × $10.00/1M = $0.00108 |
| **Subtotal** | | | **$0.002205/interaction** |

### 5. LLM Combined

- Flash: $0.0000977
- GPT-4o: $0.002205
- **Total LLM: $0.002303/interaction**

### 6. Infrastructure (amortized per interaction)

Monthly infrastructure costs at scale:

| Component | Sizing | Monthly Cost |
|---|---|---|
| GKE voice nodes (g2-standard-4) | 4 nodes avg, 10 peak (HPA) | ~$2,016 avg + burst |
| GKE API/agent nodes (e2-standard-4) | 3 nodes avg | ~$440 |
| Memorystore Redis 2GB | 1 instance HA | ~$72 |
| CockroachDB Serverless | ~50M RUs/month | ~$50 |
| Kafka (Redpanda Cloud) | Basic tier | ~$200 |
| Prometheus + monitoring | Managed | ~$150 |
| Load balancer + networking | | ~$100 |
| **Total infrastructure** | | **~$3,028/month** |

Per interaction: $3,028 / 10,000,000 = **$0.000303/interaction**

---

## Summary: All-API Scenario

All speech processing via cloud APIs (Intron ASR + Cartesia TTS).

| Component | $/Interaction | % of Total |
|---|---|---|
| ASR (blended) | $0.00720 | 51.9% |
| TTS (blended) | $0.00405 | 29.2% |
| LLM (Flash + GPT-4o) | $0.00230 | 16.6% |
| Infrastructure (amortized) | $0.00030 | 2.2% |
| **Total** | **$0.01385** | **100%** |

**$0.014/interaction — well under the $0.15 target (91% margin).**

Monthly cost at 10M interactions: **~$138,500**

---

## Summary: Hybrid Scenario (Self-Hosted ASR)

Self-hosted Whisper-Hausa on GPU nodes eliminates per-minute ASR charges. GPU node cost is captured in infrastructure.

| Component | $/Interaction | % of Total |
|---|---|---|
| ASR (self-hosted, in infra) | $0.00000 | 0% |
| TTS (blended) | $0.00405 | 55.6% |
| LLM (Flash + GPT-4o) | $0.00230 | 31.6% |
| Infrastructure (amortized, +GPU) | $0.00095 | 13.0% |
| **Total** | **$0.00729** | **100%** |

Infrastructure increases to ~$7,290/month with dedicated GPU nodes for ASR, but eliminates $72,000/month in API ASR costs.

**$0.007/interaction — 95% below target. Monthly: ~$72,900 (47% savings vs All-API).**

---

## Sensitivity Analysis

### Voice Share: 60% → 80%

| Scenario | 60% Voice | 80% Voice | Delta |
|---|---|---|---|
| All-API | $0.01385 | $0.01735 | +25.3% |
| Hybrid | $0.00729 | $0.00769 | +5.5% |

Hybrid scenario is resilient to voice share increases — ASR cost is fixed in infrastructure.

### Avg Duration: 2 min → 3 min

| Scenario | 2 min | 3 min | Delta |
|---|---|---|---|
| All-API | $0.01385 | $0.01745 | +26.0% |
| Hybrid | $0.00729 | $0.00729 | +0% |

Longer calls increase API ASR cost linearly. Self-hosted ASR is duration-independent (fixed GPU cost). TTS cost also increases slightly with longer interactions (~$0.002 additional).

### Combined Worst Case: 80% Voice + 3 min Duration

| Scenario | Cost | vs Target |
|---|---|---|
| All-API | ~$0.024 | 84% below $0.15 |
| Hybrid | ~$0.008 | 95% below $0.15 |

**Both scenarios remain well within the $0.15/interaction budget even under worst-case assumptions.**

---

## Cost Optimization Levers

1. **LLM routing ratio** — Increasing Flash share from 70% to 90% saves ~$0.0018/interaction (~$18K/month)
2. **Self-hosted ASR** — Eliminates largest variable cost component (saves 47% monthly)
3. **Response caching** — Redis-cached responses for common queries (balance, network status) can eliminate ~20% of LLM calls
4. **Batch TTS** — Pre-generate common phrases (greetings, confirmations) to reduce TTS API calls by ~30%
5. **GKE Spot VMs** — Use preemptible nodes for non-voice workloads (60-91% discount)
6. **Committed Use Discounts** — 1-year GCP CUDs for base capacity (~37% savings on compute)
