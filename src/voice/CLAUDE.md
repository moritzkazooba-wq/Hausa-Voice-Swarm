# Voice Layer

## Pipeline Architecture
Pipecat pipeline: transport → VAD → ASR → agent bridge → TTS → output

**IMPORTANT:** Read installed `pipecat-ai` source before writing code.
The API evolves rapidly — check actual class signatures.

## Components
- **Transport:** Daily WebRTC (default), Telnyx SIP (config toggle)
- **VAD:** Silero VAD — voice activity detection
- **ASR:** Intron Hausa Whisper (real), stub processor (default dev)
- **TTS:** Intron/Cartesia (real), stub processor (default dev)
- **Agent Bridge:** Connects voice pipeline to LangGraph agent orchestrator

## Dev/Prod Modes
- `USE_REAL_ASR=false` → stub ASR with simulated latency
- `USE_REAL_TTS=false` → stub TTS with simulated latency
- Stubs return canned responses to avoid API costs during development

## Telephony
- Telnyx SIP supported via config toggle (`TELEPHONY_PROVIDER=telnyx`)
- SIP INVITE handling through Pipecat transport layer
