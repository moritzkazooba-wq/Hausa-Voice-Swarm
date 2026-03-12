"""Mock resolvers for GraphQL API — replaced with real DB in Phase 3."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from src.models.customer import CustomerProfile, NetworkStatus
from src.models.transaction import ActionResult, Transaction

# --- Mock data stores ---

_CUSTOMER_1_ID = UUID("11111111-1111-1111-1111-111111111111")
_CUSTOMER_2_ID = UUID("22222222-2222-2222-2222-222222222222")

MOCK_CUSTOMERS: dict[str, CustomerProfile] = {
    "+2348012345678": CustomerProfile(
        id=_CUSTOMER_1_ID,
        phone_number="+2348012345678",
        name="Amina Bello",
        balance=Decimal("15000.50"),
        currency="NGN",
        plan="basic",
        status="active",
        region="kano",
    ),
    "+2348087654321": CustomerProfile(
        id=_CUSTOMER_2_ID,
        phone_number="+2348087654321",
        name="Musa Ibrahim",
        balance=Decimal("82300.00"),
        currency="NGN",
        plan="premium",
        status="active",
        region="lagos",
    ),
}

MOCK_TRANSACTIONS: dict[UUID, list[Transaction]] = {
    _CUSTOMER_1_ID: [
        Transaction(
            id=UUID("aaaa1111-0000-0000-0000-000000000001"),
            account_id=_CUSTOMER_1_ID,
            amount=Decimal("500.00"),
            merchant="MTN Airtime",
            date=datetime(2026, 3, 10, 14, 30, tzinfo=UTC),
            status="completed",
            type="debit",
        ),
        Transaction(
            id=UUID("aaaa1111-0000-0000-0000-000000000002"),
            account_id=_CUSTOMER_1_ID,
            amount=Decimal("20000.00"),
            merchant="Salary Credit",
            date=datetime(2026, 3, 1, 9, 0, tzinfo=UTC),
            status="completed",
            type="credit",
        ),
    ],
    _CUSTOMER_2_ID: [
        Transaction(
            id=UUID("bbbb2222-0000-0000-0000-000000000001"),
            account_id=_CUSTOMER_2_ID,
            amount=Decimal("3500.00"),
            merchant="DSTV Subscription",
            date=datetime(2026, 3, 8, 11, 15, tzinfo=UTC),
            status="completed",
            type="debit",
        ),
    ],
}

MOCK_NETWORK: dict[str, NetworkStatus] = {
    "kano": NetworkStatus(
        region="kano",
        status="healthy",
        latency_ms=45.2,
        last_checked=datetime(2026, 3, 12, 12, 0, tzinfo=UTC),
    ),
    "lagos": NetworkStatus(
        region="lagos",
        status="degraded",
        latency_ms=220.5,
        last_checked=datetime(2026, 3, 12, 12, 0, tzinfo=UTC),
    ),
}


# --- Resolver functions ---


async def get_customer(phone_number: str) -> CustomerProfile | None:
    """Look up customer by phone number."""
    return MOCK_CUSTOMERS.get(phone_number)


async def get_customers_batch(phone_numbers: list[str]) -> list[CustomerProfile | None]:
    """Batch-load customers by phone numbers (for DataLoader)."""
    return [MOCK_CUSTOMERS.get(phone) for phone in phone_numbers]


async def get_transactions(account_id: UUID, last: int = 10) -> list[Transaction]:
    """Get recent transactions for an account."""
    txns = MOCK_TRANSACTIONS.get(account_id, [])
    return txns[:last]


async def get_transactions_batch(
    account_ids: list[UUID],
) -> list[list[Transaction]]:
    """Batch-load transactions by account IDs (for DataLoader)."""
    return [MOCK_TRANSACTIONS.get(aid, []) for aid in account_ids]


async def get_network_status(region: str) -> NetworkStatus | None:
    """Get network status for a region."""
    return MOCK_NETWORK.get(region)


async def process_payment(
    phone_number: str, amount: float, merchant: str
) -> ActionResult:
    """Process a payment — always requires confirmation on first call."""
    return ActionResult(
        success=True,
        message=f"Payment of {amount} NGN to {merchant} requires confirmation.",
        reference_id="PAY-2026-00001",
        requires_confirmation=True,
    )


async def reset_pin(phone_number: str) -> ActionResult:
    """Reset PIN — always requires confirmation."""
    return ActionResult(
        success=True,
        message="PIN reset requires confirmation. A new PIN will be sent via SMS.",
        reference_id="PIN-2026-00001",
        requires_confirmation=True,
    )


async def change_plan(phone_number: str, new_plan: str) -> ActionResult:
    """Change service plan — always requires confirmation."""
    return ActionResult(
        success=True,
        message=f"Plan change to {new_plan} requires confirmation.",
        reference_id="PLAN-2026-00001",
        requires_confirmation=True,
    )


async def create_escalation_ticket(phone_number: str, issue: str) -> ActionResult:
    """Create escalation ticket — always requires confirmation."""
    return ActionResult(
        success=True,
        message=f"Escalation ticket created for: {issue}. Requires confirmation.",
        reference_id="ESC-2026-00001",
        requires_confirmation=True,
    )
