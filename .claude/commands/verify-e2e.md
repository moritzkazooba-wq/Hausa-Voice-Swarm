---
description: Run e2e tests against docker-compose stack (starts it if needed)
---
1. `docker compose ps --format json` — check if services are running and healthy
2. If all healthy: skip to step 4
3. If not running or unhealthy: `docker compose up -d --build --wait` then `sleep 5`
4. `uv run pytest tests/e2e/ -v --tb=short`
5. Report results. Do NOT shut down docker-compose.
