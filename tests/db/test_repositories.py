"""Tests for database repositories (require CockroachDB — skipped without COCKROACHDB_URL)."""

from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from src.db.models import AccountModel, Base
from src.db.repositories import AccountRepository, TransactionRepository


@pytest.fixture
async def db_session(cockroachdb_url: str):
    """Create tables and yield a session, then tear down."""
    engine = create_async_engine(cockroachdb_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    # Clean up tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


def _make_account(phone: str = "+2348012345678") -> AccountModel:
    return AccountModel(
        id=uuid4(),
        phone_number=phone,
        name="Amina Bello",
        balance=Decimal("15000.50"),
        currency="NGN",
        plan="basic",
        status="active",
        region="kano",
    )


# --- AccountRepository ---


@pytest.mark.db
@pytest.mark.asyncio
async def test_get_by_phone_found(db_session: AsyncSession) -> None:
    acct = _make_account()
    db_session.add(acct)
    await db_session.commit()

    repo = AccountRepository(db_session)
    result = await repo.get_by_phone("+2348012345678")
    assert result is not None
    assert result.phone_number == "+2348012345678"
    assert result.name == "Amina Bello"


@pytest.mark.db
@pytest.mark.asyncio
async def test_get_by_phone_not_found(db_session: AsyncSession) -> None:
    repo = AccountRepository(db_session)
    result = await repo.get_by_phone("+2340000000000")
    assert result is None


@pytest.mark.db
@pytest.mark.asyncio
async def test_get_by_id(db_session: AsyncSession) -> None:
    acct = _make_account()
    db_session.add(acct)
    await db_session.commit()

    repo = AccountRepository(db_session)
    result = await repo.get_by_id(acct.id)
    assert result is not None
    assert result.id == acct.id


@pytest.mark.db
@pytest.mark.asyncio
async def test_get_batch_by_phones(db_session: AsyncSession) -> None:
    a1 = _make_account("+2348011111111")
    a2 = _make_account("+2348022222222")
    db_session.add_all([a1, a2])
    await db_session.commit()

    repo = AccountRepository(db_session)
    results = await repo.get_batch_by_phones(
        ["+2348011111111", "+2340000000000", "+2348022222222"],
    )
    assert len(results) == 3
    assert results[0] is not None
    assert results[0].phone_number == "+2348011111111"
    assert results[1] is None
    assert results[2] is not None
    assert results[2].phone_number == "+2348022222222"


@pytest.mark.db
@pytest.mark.asyncio
async def test_update_balance(db_session: AsyncSession) -> None:
    acct = _make_account()
    db_session.add(acct)
    await db_session.commit()

    repo = AccountRepository(db_session)
    ok = await repo.update_balance(acct.id, Decimal("99999.99"))
    assert ok is True

    updated = await repo.get_by_id(acct.id)
    assert updated is not None
    assert updated.balance == Decimal("99999.99")


@pytest.mark.db
@pytest.mark.asyncio
async def test_update_plan(db_session: AsyncSession) -> None:
    acct = _make_account()
    db_session.add(acct)
    await db_session.commit()

    repo = AccountRepository(db_session)
    ok = await repo.update_plan(acct.id, "premium")
    assert ok is True

    updated = await repo.get_by_id(acct.id)
    assert updated is not None
    assert updated.plan == "premium"


# --- TransactionRepository ---


@pytest.mark.db
@pytest.mark.asyncio
async def test_get_transactions_by_account(db_session: AsyncSession) -> None:
    acct = _make_account()
    db_session.add(acct)
    await db_session.commit()

    repo = TransactionRepository(db_session)
    txn = await repo.create_transaction(
        account_id=acct.id,
        amount=Decimal("500.00"),
        merchant="MTN Airtime",
        type="debit",
    )
    assert txn.status == "pending"

    txns = await repo.get_by_account(acct.id)
    assert len(txns) == 1
    assert txns[0].merchant == "MTN Airtime"


@pytest.mark.db
@pytest.mark.asyncio
async def test_create_transaction(db_session: AsyncSession) -> None:
    acct = _make_account()
    db_session.add(acct)
    await db_session.commit()

    repo = TransactionRepository(db_session)
    txn = await repo.create_transaction(
        account_id=acct.id,
        amount=Decimal("1000.00"),
        merchant="Glo Airtime",
        type="debit",
    )
    assert txn.account_id == acct.id
    assert txn.amount == Decimal("1000.00")
    assert txn.merchant == "Glo Airtime"
    assert txn.type == "debit"
    assert txn.status == "pending"


@pytest.mark.db
@pytest.mark.asyncio
async def test_get_batch_by_accounts(db_session: AsyncSession) -> None:
    a1 = _make_account("+2348033333333")
    a2 = _make_account("+2348044444444")
    db_session.add_all([a1, a2])
    await db_session.commit()

    repo = TransactionRepository(db_session)
    await repo.create_transaction(a1.id, Decimal("100"), "M1", "debit")
    await repo.create_transaction(a1.id, Decimal("200"), "M2", "credit")
    await repo.create_transaction(a2.id, Decimal("300"), "M3", "debit")

    batched = await repo.get_batch_by_accounts([a1.id, a2.id])
    assert len(batched) == 2
    assert len(batched[0]) == 2
    assert len(batched[1]) == 1
