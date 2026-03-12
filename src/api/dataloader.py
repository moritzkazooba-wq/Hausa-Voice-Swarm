"""Strawberry DataLoader implementations for N+1 query prevention."""

from uuid import UUID

from strawberry.dataloader import DataLoader

from src.api import mock_resolvers
from src.models.customer import CustomerProfile
from src.models.transaction import Transaction


def create_account_loader() -> DataLoader[str, CustomerProfile | None]:
    """Create a DataLoader that batches customer lookups by phone number."""
    return DataLoader(load_fn=mock_resolvers.get_customers_batch)


def create_transaction_loader() -> DataLoader[UUID, list[Transaction]]:
    """Create a DataLoader that batches transaction lookups by account ID."""
    return DataLoader(load_fn=mock_resolvers.get_transactions_batch)
