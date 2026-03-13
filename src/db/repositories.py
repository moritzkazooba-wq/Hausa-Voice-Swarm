"""Repository pattern — customer data access."""

from __future__ import annotations

from src.api.mock_resolvers import MOCK_CUSTOMERS
from src.models.customer import CustomerProfile


class CustomerRepository:
    """Customer data access.

    Currently backed by in-memory mock data (``MOCK_CUSTOMERS``).
    Replace with real CockroachDB queries when ORM models are added.
    """

    async def get_by_phone(self, phone_number: str) -> CustomerProfile | None:
        """Look up a customer by phone number."""
        return MOCK_CUSTOMERS.get(phone_number)
