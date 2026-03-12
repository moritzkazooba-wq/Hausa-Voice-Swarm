"""Resolver dispatch: routes to mock or real DB resolvers based on config."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.api import mock_resolvers
from src.db.repositories import AccountRepository, TransactionRepository
from src.models.customer import CustomerProfile, NetworkStatus
from src.models.transaction import ActionResult, Transaction

# --- Batch loaders (used by DataLoaders) ---


async def get_customers_batch_db(
    session_factory: async_sessionmaker[AsyncSession],
    phone_numbers: list[str],
) -> list[CustomerProfile | None]:
    """Batch-load customers from DB."""
    async with session_factory() as session:
        repo = AccountRepository(session)
        return await repo.get_batch_by_phones(phone_numbers)


async def get_transactions_batch_db(
    session_factory: async_sessionmaker[AsyncSession],
    account_ids: list[UUID],
) -> list[list[Transaction]]:
    """Batch-load transactions from DB."""
    async with session_factory() as session:
        repo = TransactionRepository(session)
        return await repo.get_batch_by_accounts(account_ids)


# --- Network status (stays mock — no DB table for this) ---


async def get_network_status(region: str) -> NetworkStatus | None:
    """Get network status (mock — no DB table for this yet)."""
    return await mock_resolvers.get_network_status(region)


# --- Mutations (still return requires_confirmation=True) ---


async def process_payment(
    phone_number: str, amount: float, merchant: str,
) -> ActionResult:
    """Process a payment — always requires confirmation on first call."""
    return await mock_resolvers.process_payment(phone_number, amount, merchant)


async def reset_pin(phone_number: str) -> ActionResult:
    """Reset PIN — always requires confirmation."""
    return await mock_resolvers.reset_pin(phone_number)


async def change_plan(phone_number: str, new_plan: str) -> ActionResult:
    """Change plan — always requires confirmation."""
    return await mock_resolvers.change_plan(phone_number, new_plan)


async def create_escalation_ticket(
    phone_number: str, issue: str,
) -> ActionResult:
    """Create escalation ticket — always requires confirmation."""
    return await mock_resolvers.create_escalation_ticket(phone_number, issue)
