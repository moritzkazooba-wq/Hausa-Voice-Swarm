---
description: Scaffold or extend the Pipecat voice pipeline for Hausa Voice Swarm
---

# /pipecat:init — Scaffold Pipecat Voice Pipeline

You are helping build a Pipecat voice pipeline for the Hausa Voice Swarm project — a mobile money customer support system for Hausa-speaking users.

## Context

- Project uses Pipecat (v0.0.105+) for voice pipeline orchestration
- Pipeline: DailyTransport → SileroVAD → ASR → Agent Bridge → TTS → Output
- The agent layer (intent classifier, supervisor, domain agents) is already implemented in `src/agents/`
- Prometheus metrics are defined in `src/metrics/definitions.py`
- Config is in `src/config/settings.py` (ASRSettings, TTSSettings, TelephonySettings)

## Step 1: Ask what to scaffold

Use AskUserQuestion to determine what the user wants:
- **Full pipeline** — scaffold `src/voice/pipeline.py` with transport, VAD, STT, agent bridge, TTS
- **ASR only** — implement `src/voice/asr.py` (stub + real Intron/Whisper)
- **TTS only** — implement `src/voice/tts.py` (stub + real Intron/Cartesia)
- **VAD only** — implement `src/voice/vad.py` (Silero VAD config)

## Step 2: Read existing code first

ALWAYS read these files before writing any code:
1. `src/voice/CLAUDE.md` — architecture constraints
2. `src/config/settings.py` — ASRSettings, TTSSettings, TelephonySettings
3. `src/agents/supervisor.py` — `route_to_agent()` is the agent entry point
4. `src/metrics/definitions.py` — metrics to instrument (asr_latency_ms, tts_latency_ms, voice_to_voice_latency_ms, active_voice_sessions)

ALWAYS read the installed pipecat source to verify class signatures:
- `.venv/lib/python3.12/site-packages/pipecat/pipeline/pipeline.py` — `Pipeline(processors=[...])`
- `.venv/lib/python3.12/site-packages/pipecat/pipeline/runner.py` — `PipelineRunner`
- `.venv/lib/python3.12/site-packages/pipecat/pipeline/task.py` — `PipelineTask`
- `.venv/lib/python3.12/site-packages/pipecat/transports/daily/transport.py` — `DailyTransport`, `DailyParams`
- `.venv/lib/python3.12/site-packages/pipecat/audio/vad/silero.py` — `SileroVADAnalyzer`, `VADParams`
- `.venv/lib/python3.12/site-packages/pipecat/services/stt_service.py` — `STTService` base class
- `.venv/lib/python3.12/site-packages/pipecat/services/tts_service.py` — `TTSService` base class
- `.venv/lib/python3.12/site-packages/pipecat/frames/frames.py` — Frame types

## Step 3: Implementation patterns

### ASR Stub Pattern
```python
class StubSTTService(STTService):
    """Stub STT that returns canned transcriptions with simulated latency."""
    # Simulate 200-500ms latency
    # Return canned Hausa phrases for testing
    # Observe asr_latency_ms metric
```

### TTS Stub Pattern
```python
class StubTTSService(TTSService):
    """Stub TTS that returns silent audio with simulated latency."""
    # Simulate 150-400ms latency
    # Return silent audio frames
    # Observe tts_latency_ms metric
```

### Pipeline Pattern
```python
pipeline = Pipeline([
    transport.input(),        # DailyTransport input
    stt,                      # STTService (stub or real)
    agent_bridge,             # Custom FrameProcessor bridging to LangGraph
    tts,                      # TTSService (stub or real)
    transport.output(),       # DailyTransport output
])
task = PipelineTask(pipeline, params=PipelineTaskParams(
    allow_interruptions=True,
    enable_metrics=True,
))
runner = PipelineRunner()
await runner.run(task)
```

### Agent Bridge Pattern
```python
class AgentBridgeProcessor(FrameProcessor):
    """Bridges Pipecat STT output to LangGraph agent orchestrator."""
    async def process_frame(self, frame, direction):
        if isinstance(frame, TranscriptionFrame):
            result, classification = await route_to_agent(session_id, frame.text)
            await self.push_frame(TTSSpeakFrame(text=result.message))
        else:
            await self.push_frame(frame, direction)
```

## Step 4: Dev/Prod mode

- Check `USE_REAL_ASR` / `USE_REAL_TTS` env vars from settings
- If false (default): use stub processors with simulated latency
- If true: use real service implementations (Intron API, etc.)
- ALWAYS instrument with Prometheus metrics from `src/metrics/definitions`
- ALWAYS use structlog for logging

## Step 5: Testing

- Write tests in `tests/voice/`
- Mock the transport layer — never require a real Daily room
- Test that metrics are observed after processing
- Test stub latency simulation
- Run `/verify` after implementation

## Cross-cutting rules (from CLAUDE.md)
- Type hints on ALL functions, mypy strict
- Async everywhere — no blocking calls
- Agent responses: max 2 sentences for low-literacy users
- Use `uv add <pkg>` for new deps, NEVER pip
