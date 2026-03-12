---
description: Run full verification suite (lint, typecheck, unit tests — excludes e2e)
---
Run these checks in sequence and report results:
1. `uv run ruff check src/ tests/` — report issues (do NOT auto-fix)
2. `uv run mypy src/` — report errors
3. `uv run pytest tests/ -v --tb=short --ignore=tests/e2e` — report failures
Summarize: total errors/warnings per tool, and whether this phase is ready to commit.
If there are ruff issues, ask whether to auto-fix with `uv run ruff check --fix`.
