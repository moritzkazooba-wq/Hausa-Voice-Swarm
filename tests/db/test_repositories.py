"""Tests for customer repository."""

from __future__ import annotations

import pytest
from src.db.repositories import CustomerRepository


@pytest.mark.asyncio
async def test_get_customer_by_phone_found() -> None:
    """Known phone number returns a CustomerProfile."""
    repo = CustomerRepository()
    customer = await repo.get_by_phone("+2348012345678")
    assert customer is not None
    assert customer.name == "Amina Bello"


@pytest.mark.asyncio
async def test_get_customer_by_phone_not_found() -> None:
    """Unknown phone number returns None."""
    repo = CustomerRepository()
    customer = await repo.get_by_phone("+2340000000000")
    assert customer is None
