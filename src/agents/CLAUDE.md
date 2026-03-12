# Agents Layer

## Architecture
- **Orchestrator-worker pattern** via LangGraph StateGraph
- Orchestrator receives user intent, routes to one of 4 domain agents
- Domain agents: balance, transfer, bills, general

## Intent Classification
- Uses `paraphrase-multilingual-MiniLM-L12-v2` sentence-transformers model
- Cosine similarity against intent embeddings
- Supports Hausa + English code-switching

## Cost Routing
- LiteLLM abstracts LLM calls
- GPT-4o for complex tasks (transfer confirmation, dispute resolution)
- Gemini Flash for simple tasks (balance check, FAQ)

## Testing
- Mock httpx calls via `pytest-httpx`
- Mock LiteLLM responses for deterministic tests
- Test intent classification accuracy with known Hausa phrases
