"""Strawberry GraphQL schema: types, queries, and mutations."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

import strawberry
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from strawberry.fastapi import BaseContext
from strawberry.types import Info

from src.api import resolvers
from src.api.dataloader import create_account_loader, create_transaction_loader
from src.models.customer import CustomerProfile, NetworkStatus
from src.models.transaction import ActionResult, Transaction

# --- Strawberry types ---


@strawberry.type
class AccountType:
    """Mobile money customer account."""

    id: strawberry.ID
    phone_number: str
    name: str
    balance: Decimal
    currency: str
    plan: str
    status: str
    region: str


@strawberry.type
class TransactionType:
    """Financial transaction record."""

    id: strawberry.ID
    account_id: strawberry.ID
    amount: Decimal
    merchant: str
    date: datetime
    status: str
    type: str


@strawberry.type
class ActionResultType:
    """Result of an agent action."""

    success: bool
    message: str
    reference_id: str | None
    requires_confirmation: bool


@strawberry.type
class NetworkStatusType:
    """Regional network health status."""

    region: str
    status: str
    latency_ms: float
    last_checked: datetime


# --- Helper to convert models to Strawberry types ---


def _customer_to_account(customer: CustomerProfile) -> AccountType:
    return AccountType(
        id=strawberry.ID(str(customer.id)),
        phone_number=customer.phone_number,
        name=customer.name,
        balance=customer.balance,
        currency=customer.currency,
        plan=customer.plan,
        status=customer.status,
        region=customer.region,
    )


def _txn_to_type(txn: Transaction) -> TransactionType:
    return TransactionType(
        id=strawberry.ID(str(txn.id)),
        account_id=strawberry.ID(str(txn.account_id)),
        amount=txn.amount,
        merchant=txn.merchant,
        date=txn.date,
        status=txn.status,
        type=txn.type,
    )


def _action_to_type(result: ActionResult) -> ActionResultType:
    return ActionResultType(
        success=result.success,
        message=result.message,
        reference_id=result.reference_id,
        requires_confirmation=result.requires_confirmation,
    )


def _network_to_type(ns: NetworkStatus) -> NetworkStatusType:
    return NetworkStatusType(
        region=ns.region,
        status=ns.status,
        latency_ms=ns.latency_ms,
        last_checked=ns.last_checked,
    )


# --- Context type for DataLoaders ---


class GraphQLContext(BaseContext):
    """Custom context providing DataLoaders."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
    ) -> None:
        super().__init__()
        self.account_loader = create_account_loader(session_factory)
        self.transaction_loader = create_transaction_loader(session_factory)


# --- Query ---


@strawberry.type
class Query:
    """GraphQL queries for the Hausa Voice Swarm API."""

    @strawberry.field
    async def account_balance(
        self, info: Info[GraphQLContext, None], phone_number: str
    ) -> AccountType | None:
        """Look up account by phone number."""
        customer = await info.context.account_loader.load(phone_number)
        if customer is None:
            return None
        return _customer_to_account(customer)

    @strawberry.field
    async def transaction_history(
        self,
        info: Info[GraphQLContext, None],
        account_id: strawberry.ID,
        last: int = 10,
    ) -> list[TransactionType]:
        """Get recent transactions for an account."""
        uid = UUID(str(account_id))
        txns = await info.context.transaction_loader.load(uid)
        return [_txn_to_type(t) for t in txns[:last]]

    @strawberry.field
    async def network_status(self, region: str) -> NetworkStatusType | None:
        """Get network health status for a region."""
        ns = await resolvers.get_network_status(region)
        if ns is None:
            return None
        return _network_to_type(ns)


# --- Mutation ---


@strawberry.type
class Mutation:
    """GraphQL mutations — all financial mutations require confirmation."""

    @strawberry.mutation
    async def process_payment(
        self, phone_number: str, amount: float, merchant: str
    ) -> ActionResultType:
        """Process a payment (requires confirmation)."""
        result = await resolvers.process_payment(phone_number, amount, merchant)
        return _action_to_type(result)

    @strawberry.mutation
    async def reset_pin(self, phone_number: str) -> ActionResultType:
        """Reset account PIN (requires confirmation)."""
        result = await resolvers.reset_pin(phone_number)
        return _action_to_type(result)

    @strawberry.mutation
    async def change_plan(
        self, phone_number: str, new_plan: str
    ) -> ActionResultType:
        """Change service plan (requires confirmation)."""
        result = await resolvers.change_plan(phone_number, new_plan)
        return _action_to_type(result)

    @strawberry.mutation
    async def create_escalation_ticket(
        self, phone_number: str, issue: str
    ) -> ActionResultType:
        """Create an escalation ticket (requires confirmation)."""
        result = await resolvers.create_escalation_ticket(phone_number, issue)
        return _action_to_type(result)


# --- Schema ---

schema = strawberry.Schema(query=Query, mutation=Mutation)
