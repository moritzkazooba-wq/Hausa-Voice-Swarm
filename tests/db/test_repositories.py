"""Tests for repository pattern implementations."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

import pytest
from src.db.repositories import CustomerRepository, TransactionRepository


@pytest.mark.asyncio
async def test_get_customer_by_phone_found() -> None:
    repo = CustomerRepository()
    customer = await repo.get_by_phone("+2348012345678")
    assert customer is not None
    assert customer.name == "Amina Bello"


@pytest.mark.asyncio
async def test_get_customer_by_phone_not_found() -> None:
    repo = CustomerRepository()
    customer = await repo.get_by_phone("+2349999999999")
    assert customer is None


@pytest.mark.asyncio
async def test_get_balance() -> None:
    repo = CustomerRepository()
    balance = await repo.get_balance("+2348012345678")
    assert balance is not None
    assert balance == Decimal("15000.50")


@pytest.mark.asyncio
async def test_get_balance_not_found() -> None:
    repo = CustomerRepository()
    balance = await repo.get_balance("+2349999999999")
    assert balance is None


@pytest.mark.asyncio
async def test_get_transactions_by_account() -> None:
    repo = TransactionRepository()
    account_id = UUID("11111111-1111-1111-1111-111111111111")
    txns = await repo.get_by_account(account_id)
    assert len(txns) == 2


@pytest.mark.asyncio
async def test_get_transactions_limit() -> None:
    repo = TransactionRepository()
    account_id = UUID("11111111-1111-1111-1111-111111111111")
    txns = await repo.get_by_account(account_id, limit=1)
    assert len(txns) == 1


@pytest.mark.asyncio
async def test_get_transactions_empty() -> None:
    repo = TransactionRepository()
    txns = await repo.get_by_account(UUID("99999999-9999-9999-9999-999999999999"))
    assert txns == []
