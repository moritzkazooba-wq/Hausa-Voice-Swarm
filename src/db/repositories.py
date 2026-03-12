"""Repository pattern implementations for CockroachDB."""

from decimal import Decimal
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import AccountModel, TransactionModel
from src.models.customer import CustomerProfile
from src.models.transaction import Transaction


class AccountRepository:
    """Repository for customer account operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_phone(self, phone_number: str) -> CustomerProfile | None:
        """Look up a customer by phone number."""
        stmt = select(AccountModel).where(AccountModel.phone_number == phone_number)
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return row.to_pydantic() if row else None

    async def get_by_id(self, account_id: UUID) -> CustomerProfile | None:
        """Look up a customer by account ID."""
        stmt = select(AccountModel).where(AccountModel.id == account_id)
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return row.to_pydantic() if row else None

    async def get_batch_by_phones(
        self, phone_numbers: list[str],
    ) -> list[CustomerProfile | None]:
        """Batch-load customers by phone numbers (for DataLoader)."""
        stmt = select(AccountModel).where(
            AccountModel.phone_number.in_(phone_numbers),
        )
        result = await self._session.execute(stmt)
        rows = {r.phone_number: r for r in result.scalars().all()}
        return [
            rows[phone].to_pydantic() if phone in rows else None
            for phone in phone_numbers
        ]

    async def update_balance(
        self, account_id: UUID, new_balance: Decimal,
    ) -> bool:
        """Update account balance. Returns True if account exists."""
        stmt = (
            update(AccountModel)
            .where(AccountModel.id == account_id)
            .values(balance=new_balance)
        )
        result = await self._session.execute(stmt)
        await self._session.commit()
        return bool(result.rowcount)  # type: ignore[attr-defined]

    async def update_plan(self, account_id: UUID, new_plan: str) -> bool:
        """Update account plan. Returns True if account exists."""
        stmt = (
            update(AccountModel)
            .where(AccountModel.id == account_id)
            .values(plan=new_plan)
        )
        result = await self._session.execute(stmt)
        await self._session.commit()
        return bool(result.rowcount)  # type: ignore[attr-defined]


class TransactionRepository:
    """Repository for transaction operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_account(
        self, account_id: UUID, limit: int = 10,
    ) -> list[Transaction]:
        """Get recent transactions for an account, newest first."""
        stmt = (
            select(TransactionModel)
            .where(TransactionModel.account_id == account_id)
            .order_by(TransactionModel.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [row.to_pydantic() for row in result.scalars().all()]

    async def get_batch_by_accounts(
        self, account_ids: list[UUID],
    ) -> list[list[Transaction]]:
        """Batch-load transactions by account IDs (for DataLoader)."""
        stmt = (
            select(TransactionModel)
            .where(TransactionModel.account_id.in_(account_ids))
            .order_by(TransactionModel.created_at.desc())
        )
        result = await self._session.execute(stmt)
        rows_by_account: dict[UUID, list[Transaction]] = {
            aid: [] for aid in account_ids
        }
        for row in result.scalars().all():
            rows_by_account[row.account_id].append(row.to_pydantic())
        return [rows_by_account[aid] for aid in account_ids]

    async def create_transaction(
        self,
        account_id: UUID,
        amount: Decimal,
        merchant: str,
        type: str,
    ) -> Transaction:
        """Create a new transaction record."""
        txn = TransactionModel(
            account_id=account_id,
            amount=amount,
            merchant=merchant,
            type=type,
            status="pending",
        )
        self._session.add(txn)
        await self._session.commit()
        await self._session.refresh(txn)
        return txn.to_pydantic()
