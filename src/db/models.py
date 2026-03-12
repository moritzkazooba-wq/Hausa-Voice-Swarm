"""SQLAlchemy async ORM models for CockroachDB."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from src.models.customer import CustomerProfile
from src.models.transaction import Transaction


class Base(DeclarativeBase):
    """Base class for all ORM models."""


class AccountModel(Base):
    """Mobile money customer account."""

    __tablename__ = "accounts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    phone_number: Mapped[str] = mapped_column(String(15), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    balance: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    currency: Mapped[str] = mapped_column(String(3), default="NGN")
    plan: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(20))
    region: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    transactions: Mapped[list["TransactionModel"]] = relationship(
        back_populates="account",
    )

    def to_pydantic(self) -> CustomerProfile:
        """Convert to Pydantic CustomerProfile."""
        return CustomerProfile.model_construct(
            id=self.id,
            phone_number=self.phone_number,
            name=self.name,
            balance=self.balance,
            currency=self.currency,
            plan=self.plan,
            status=self.status,
            region=self.region,
        )


class TransactionModel(Base):
    """Financial transaction record."""

    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("accounts.id"), index=True,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    merchant: Mapped[str] = mapped_column(String(200))
    type: Mapped[str] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    account: Mapped["AccountModel"] = relationship(back_populates="transactions")

    def to_pydantic(self) -> Transaction:
        """Convert to Pydantic Transaction."""
        date = self.created_at if self.created_at.tzinfo else self.created_at.replace(tzinfo=UTC)
        return Transaction.model_construct(
            id=self.id,
            account_id=self.account_id,
            amount=self.amount,
            merchant=self.merchant,
            date=date,
            status=self.status,  # type: ignore[arg-type]
            type=self.type,  # type: ignore[arg-type]
        )


class PlanModel(Base):
    """Service plan definition."""

    __tablename__ = "plans"

    name: Mapped[str] = mapped_column(String(50), primary_key=True)
    monthly_fee: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    data_gb: Mapped[int]
    description: Mapped[str] = mapped_column(String(500))
