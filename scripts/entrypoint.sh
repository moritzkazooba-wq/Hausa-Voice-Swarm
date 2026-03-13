#!/usr/bin/env bash
set -euo pipefail

# ── Wait for CockroachDB ────────────────────────────────────────────
echo "Waiting for CockroachDB..."
elapsed=0
until python -c "
import asyncio, asyncpg, os, sys
async def check():
    url = os.environ.get('COCKROACHDB_URL', '')
    dsn = url.replace('postgresql+asyncpg://', 'postgresql://')
    try:
        conn = await asyncpg.connect(dsn)
        await conn.close()
    except Exception as e:
        print(f'  cockroachdb not ready: {e}', file=sys.stderr)
        sys.exit(1)
asyncio.run(check())
" 2>/dev/null; do
    elapsed=$((elapsed + 2))
    if [ "$elapsed" -ge 60 ]; then
        echo "ERROR: CockroachDB not ready after 60s" >&2
        exit 1
    fi
    echo "  retrying in 2s ($elapsed/60)..."
    sleep 2
done
echo "CockroachDB ready."

# ── Wait for Redis ──────────────────────────────────────────────────
echo "Waiting for Redis..."
elapsed=0
until python -c "
import redis, os, sys
url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
try:
    r = redis.from_url(url)
    r.ping()
except Exception as e:
    print(f'  redis not ready: {e}', file=sys.stderr)
    sys.exit(1)
" 2>/dev/null; do
    elapsed=$((elapsed + 2))
    if [ "$elapsed" -ge 60 ]; then
        echo "ERROR: Redis not ready after 60s" >&2
        exit 1
    fi
    echo "  retrying in 2s ($elapsed/60)..."
    sleep 2
done
echo "Redis ready."

# ── Alembic migrations ──────────────────────────────────────────────
if [ -f alembic.ini ]; then
    echo "Running Alembic migrations..."
    alembic upgrade head || echo "WARN: alembic upgrade failed (may have no migrations yet)"
else
    echo "SKIP: no alembic.ini found"
fi

# ── Seed data ───────────────────────────────────────────────────────
echo "Checking seed data..."
python -m src.db.seed --check-empty || echo "WARN: seed check failed (non-critical)"

# ── Start application ───────────────────────────────────────────────
echo "Starting uvicorn..."
exec uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --factory --log-level info
