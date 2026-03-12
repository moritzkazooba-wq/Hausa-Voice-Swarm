# API Layer

## Endpoints
- **`/graphql`** — Strawberry GraphQL (queries + mutations + subscriptions)
- **`/health`** — Returns 503 during startup, 200 when ready
- **`/metrics`** — Prometheus metrics endpoint
- **`/test/simulate-call`** — Test endpoint: simulates a voice call flow
  - Uses `asyncio.Event` for sync between request and agent pipeline
  - 10-second timeout

## GraphQL
- Strawberry with FastAPI integration
- DataLoader for N+1 query prevention
- Queries: session status, customer info, transaction history
- Mutations: initiate call, end call, trigger transfer

## Patterns
- All resolvers are async
- Use dependency injection for DB sessions and Redis
- Authentication via middleware (future phase)
