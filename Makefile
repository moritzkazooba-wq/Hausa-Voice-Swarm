.PHONY: dev-up dev-down seed test test-e2e lint typecheck verify

dev-up:
	docker compose up -d --build

dev-down:
	docker compose down -v

seed:
	docker compose exec app python -m src.db.seed

test:
	uv run pytest tests/ -v --ignore=tests/e2e

test-e2e:
	docker compose up -d --build --wait; sleep 5; uv run pytest tests/e2e/ -v; docker compose down

lint:
	uv run ruff check src/ tests/

typecheck:
	uv run mypy src/

verify: lint typecheck test
