# Database Layer

## CockroachDB
- **REGIONAL BY ROW** for multi-region data locality
- SQLAlchemy async with asyncpg driver
- Repository pattern: one repository class per aggregate root
- LOCALITY clauses wrapped in `try/except` for local dev (single-node CockroachDB)

## Redis Session Store
- Session cache with 30-minute TTL
- Stores active call state, agent context, conversation history
- Keys: `session:{call_id}` → JSON-serialized Pydantic model

## Migrations
- Alembic for schema migrations
- Always test migrations against single-node CockroachDB first

## Testing
- DB tests use `@pytest.mark.db` marker
- Skipped automatically if `COCKROACHDB_URL` not set
- Use fakeredis for Redis tests (no real server needed)
