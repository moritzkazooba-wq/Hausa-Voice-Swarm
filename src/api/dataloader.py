"""Strawberry DataLoader implementations for N+1 query prevention."""

from functools import partial
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from strawberry.dataloader import DataLoader

from src.api import mock_resolvers
from src.api.resolvers import get_customers_batch_db, get_transactions_batch_db
from src.models.customer import CustomerProfile
from src.models.transaction import Transaction


def create_account_loader(
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> DataLoader[str, CustomerProfile | None]:
    """Create a DataLoader that batches customer lookups by phone number."""
    if session_factory is not None:
        return DataLoader(
            load_fn=partial(get_customers_batch_db, session_factory),
        )
    return DataLoader(load_fn=mock_resolvers.get_customers_batch)


def create_transaction_loader(
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> DataLoader[UUID, list[Transaction]]:
    """Create a DataLoader that batches transaction lookups by account ID."""
    if session_factory is not None:
        return DataLoader(
            load_fn=partial(get_transactions_batch_db, session_factory),
        )
    return DataLoader(load_fn=mock_resolvers.get_transactions_batch)
