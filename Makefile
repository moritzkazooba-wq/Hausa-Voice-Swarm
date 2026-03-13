.PHONY: lint typecheck test test-e2e dev-up dev-down seed \
       load-smoke load-local load-ramp load-sustained load-burst load-chaos load-report

# ── Code quality ────────────────────────────────────────────────────
lint:
	uv run ruff check src/ tests/

typecheck:
	uv run mypy src/

test:
	uv run pytest tests/ -v --ignore=tests/e2e

test-e2e:
	uv run pytest tests/e2e/ -v

# ── Local dev ─────────────────────────────────────────────────────
dev-up:
	docker compose up -d

dev-down:
	docker compose down

seed:
	@echo "Infrastructure running — mock data seeded via mock_resolvers (no DB seed needed)"

# ── Load tests (local) ─────────────────────────────────────────────
BASE_URL ?= http://localhost:8000

load-smoke:
	k6 run --env BASE_URL=$(BASE_URL) benchmarks/local/smoke.js

load-local:
	k6 run --env BASE_URL=$(BASE_URL) benchmarks/local/local_load.js

# ── Load tests (cluster — REQUIRES GKE) ────────────────────────────
CLUSTER_URL ?= http://voice-pipeline.hausa-voice-swarm.svc:8000

load-ramp:
	k6 run --env BASE_URL=$(CLUSTER_URL) benchmarks/cluster/ramp_up.js

load-sustained:
	k6 run --env BASE_URL=$(CLUSTER_URL) benchmarks/cluster/sustained.js

load-burst:
	k6 run --env BASE_URL=$(CLUSTER_URL) benchmarks/cluster/burst.js

load-chaos:
	k6 run --env BASE_URL=$(CLUSTER_URL) benchmarks/cluster/failure.js

# ── Reporting ───────────────────────────────────────────────────────
PROMETHEUS_URL ?= http://localhost:9090

load-report:
	uv run python benchmarks/collect_results.py --prometheus $(PROMETHEUS_URL)
