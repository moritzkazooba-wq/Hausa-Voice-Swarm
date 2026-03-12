---
description: Debug, test, or modify the running Pipecat voice pipeline
---

# /pipecat:voice — Voice Pipeline Operations

You are helping operate and debug the Pipecat voice pipeline for Hausa Voice Swarm.

## Available Operations

Use AskUserQuestion to determine what the user wants:

### 1. Test Pipeline Locally
- Start docker compose stack: `docker compose up -d redis cockroachdb redpanda`
- Run the voice pipeline: `uv run python -m src.voice.pipeline`
- Check `/health` and `/metrics` endpoints
- Verify Prometheus metrics are being recorded

### 2. Debug Audio Issues
Read these files to understand the pipeline state:
- `src/voice/pipeline.py` — main pipeline orchestration
- `src/voice/asr.py` — ASR processor (check if stub or real)
- `src/voice/tts.py` — TTS processor (check if stub or real)
- `src/voice/vad.py` — VAD configuration
- `src/config/settings.py` — check USE_REAL_ASR, USE_REAL_TTS settings

Common issues:
- **No audio output**: Check TTS service initialization, verify `audio_out_enabled=True` in DailyParams
- **No transcription**: Check ASR service, verify VAD is detecting speech
- **High latency**: Check `hsv_voice_to_voice_latency_ms` metric, profile each stage
- **Agent not responding**: Check agent bridge → `route_to_agent()` call, verify intent classification

### 3. Switch ASR/TTS Provider
- To switch to real ASR: Set `USE_REAL_ASR=true` and `INTRON_API_KEY=<key>` in `.env`
- To switch to real TTS: Set `USE_REAL_TTS=true` in `.env`
- To switch transport: Set `TELEPHONY_PROVIDER=daily|telnyx|stub` in `.env`

### 4. Add Pipeline Processor
When adding a new processor to the pipeline:
1. Read `src/voice/pipeline.py` to understand current processor chain
2. Read the pipecat FrameProcessor base class: `.venv/lib/python3.12/site-packages/pipecat/processors/frame_processor.py`
3. Create new processor extending `FrameProcessor`
4. Implement `async def process_frame(self, frame: Frame, direction: FrameDirection)`
5. Insert into the pipeline processor list at the correct position
6. Add Prometheus metrics instrumentation
7. Write tests in `tests/voice/`

### 5. Monitor Metrics
Key metrics to check:
- `hsv_active_voice_sessions` — current session count
- `hsv_voice_to_voice_latency_ms` — end-to-end latency
- `hsv_asr_latency_ms` — speech recognition latency
- `hsv_tts_latency_ms` — text-to-speech latency
- `hsv_llm_latency_ms` — LLM response latency
- `hsv_intent_classification_total` — intent distribution
- `hsv_tool_execution_total` — agent action counts

Fetch metrics: `curl http://localhost:8000/metrics`

## Important

- ALWAYS read installed pipecat source before modifying pipeline code — the API evolves rapidly
- ALWAYS use structlog for logging, not print or loguru
- ALWAYS instrument with Prometheus metrics from `src/metrics/definitions`
- Run `/verify` after any changes
