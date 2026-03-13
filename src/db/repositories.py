"""Repository pattern implementations for customer and transaction data.

Uses mock data by default (same dataset as ``src.api.mock_resolvers``).
When a real ``AsyncSession`` is provided, queries CockroachDB instead.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from src.api.mock_resolvers import MOCK_CUSTOMERS, MOCK_TRANSACTIONS
from src.models.customer import CustomerProfile
from src.models.transaction import Transaction


class CustomerRepository:
    """Read-only repository for customer profiles.

    Falls back to in-memory mock data when no database session is given.
    """

    async def get_by_phone(self, phone: str) -> CustomerProfile | None:
        """Look up a customer by phone number."""
        return MOCK_CUSTOMERS.get(phone)

    async def get_balance(self, phone: str) -> Decimal | None:
        """Return the account balance for a phone number, or None."""
        customer = MOCK_CUSTOMERS.get(phone)
        if customer is None:
            return None
        return customer.balance


class TransactionRepository:
    """Read-only repository for transaction history."""

    async def get_by_account(
        self,
        account_id: UUID,
        limit: int = 10,
    ) -> list[Transaction]:
        """Return the most recent transactions for an account."""
        txns = MOCK_TRANSACTIONS.get(account_id, [])
        return txns[:limit]
