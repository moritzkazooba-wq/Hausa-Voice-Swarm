"""Seed script: populate CockroachDB with realistic test data.

Usage:
    python -m src.db.seed               # seed unconditionally
    python -m src.db.seed --check-empty  # only seed if accounts table is empty
"""

import argparse
import asyncio
import random
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import DatabaseSettings
from src.db.engine import dispose_engine, get_session_factory, init_engine
from src.db.models import AccountModel, PlanModel, TransactionModel

# --- Hausa names ---

FIRST_NAMES = [
    "Amina", "Musa", "Fatima", "Ibrahim", "Aisha", "Usman", "Hauwa",
    "Abdullahi", "Zainab", "Suleiman", "Hadiza", "Yusuf", "Halima",
    "Bashir", "Maryam", "Kabiru", "Safiya", "Dauda", "Bilkisu", "Garba",
    "Nafisa", "Aliyu", "Rabi", "Ismail", "Laraba", "Shehu", "Asma'u",
    "Bello", "Hassana", "Adamu", "Firdausi", "Haruna", "Jamila", "Danjuma",
    "Rahama", "Sa'idu", "Balkis", "Lawal", "Murja", "Tijjani", "Habiba",
    "Sanusi", "Sadiya", "Tanko", "Zuwaira", "Buhari", "Hadija", "Yunusa",
    "Barira", "Mamman",
]

SURNAMES = [
    "Bello", "Ibrahim", "Mohammed", "Abubakar", "Yusuf", "Abdullahi",
    "Usman", "Suleiman", "Garba", "Musa", "Shehu", "Adamu", "Danjuma",
    "Lawal", "Aliyu", "Haruna", "Tanko", "Buhari", "Sanusi", "Dauda",
    "Waziri", "Dikko", "Rabiu", "Tukur", "Ringim", "Fagge", "Gwandu",
    "Katsina", "Zazzau", "Bauchi", "Gombe", "Dutse", "Birnin", "Sokoto",
    "Kebbi", "Zamfara", "Daura", "Funtua", "Malumfashi", "Kankia",
    "Bakori", "Dandume", "Mashi", "Kafur", "Safana", "Batagarawa",
    "Charanchi", "Kurfi", "Musawa", "Matazu",
]

REGIONS = ["kano", "lagos", "abuja", "kaduna", "sokoto", "maiduguri"]

MERCHANTS = [
    "MTN Airtime", "Glo Airtime", "Airtel Airtime", "9mobile Airtime",
    "DSTV Subscription", "GOtv Subscription", "Startimes",
    "PHCN Electricity", "KEDCO Electricity", "Water Board",
    "Dangote Cement", "BUA Foods", "Shoprite", "SPAR",
    "Total Fuel", "NNPC Fuel", "Market Purchase", "School Fees",
    "Hospital Bill", "Salary Credit", "Transfer In", "Transfer Out",
    "Bet9ja", "POS Withdrawal", "ATM Withdrawal",
]

PLANS_DATA = [
    ("basic", Decimal("500.00"), 1, "Basic plan — 1 GB data, standard support"),
    ("standard", Decimal("1500.00"), 5, "Standard plan — 5 GB data, priority support"),
    ("premium", Decimal("3000.00"), 15, "Premium plan — 15 GB data, dedicated agent"),
    ("enterprise", Decimal("10000.00"), 50, "Enterprise plan — 50 GB data, SLA guarantee"),
    ("student", Decimal("300.00"), 2, "Student plan — 2 GB data, discounted rate"),
]


def _random_phone() -> str:
    """Generate a random Nigerian phone number."""
    return f"+234{random.randint(7000000000, 9099999999)}"


def _random_balance() -> Decimal:
    """Generate a balance with 70/20/10 distribution."""
    r = random.random()
    if r < 0.70:
        return Decimal(str(round(random.uniform(100, 20000), 2)))
    if r < 0.90:
        return Decimal(str(round(random.uniform(20000, 100000), 2)))
    return Decimal(str(round(random.uniform(100000, 500000), 2)))


async def _is_empty(session: AsyncSession) -> bool:
    """Check if the accounts table is empty."""
    result = await session.execute(select(func.count()).select_from(AccountModel))
    count = result.scalar_one()
    return count == 0


async def _seed_plans(session: AsyncSession) -> None:
    """Insert plan definitions."""
    rows = [
        {"name": name, "monthly_fee": fee, "data_gb": gb, "description": desc}
        for name, fee, gb, desc in PLANS_DATA
    ]
    await session.execute(insert(PlanModel), rows)
    await session.commit()
    print(f"  Seeded {len(rows)} plans")


async def _seed_accounts(session: AsyncSession, count: int = 10_000) -> list[dict[str, object]]:
    """Insert accounts and return their data for transaction generation."""
    plan_names = [p[0] for p in PLANS_DATA]
    accounts = []
    phones_seen: set[str] = set()

    for _ in range(count):
        phone = _random_phone()
        while phone in phones_seen:
            phone = _random_phone()
        phones_seen.add(phone)

        account = {
            "id": uuid.uuid4(),
            "phone_number": phone,
            "name": f"{random.choice(FIRST_NAMES)} {random.choice(SURNAMES)}",
            "balance": _random_balance(),
            "currency": "NGN",
            "plan": random.choice(plan_names),
            "status": random.choices(["active", "suspended", "closed"], weights=[90, 8, 2])[0],
            "region": random.choice(REGIONS),
        }
        accounts.append(account)

    # Bulk insert in batches of 2000
    batch_size = 2000
    for i in range(0, len(accounts), batch_size):
        batch = accounts[i : i + batch_size]
        await session.execute(insert(AccountModel), batch)
    await session.commit()
    print(f"  Seeded {len(accounts)} accounts")
    return accounts


async def _seed_transactions(
    session: AsyncSession,
    accounts: list[dict[str, object]],
    count: int = 100_000,
) -> None:
    """Insert transactions spread over 90 days."""
    now = datetime.now(tz=UTC)
    txns = []

    for _ in range(count):
        acct = random.choice(accounts)
        days_ago = random.randint(0, 90)
        hours_ago = random.randint(0, 23)
        is_debit = random.random() < 0.60

        txns.append({
            "id": uuid.uuid4(),
            "account_id": acct["id"],
            "amount": Decimal(str(round(random.uniform(50, 50000), 2))),
            "merchant": random.choice(MERCHANTS),
            "type": "debit" if is_debit else "credit",
            "status": random.choices(
                ["completed", "pending", "failed"], weights=[85, 10, 5],
            )[0],
            "created_at": now - timedelta(days=days_ago, hours=hours_ago),
        })

    # Bulk insert in batches of 5000
    batch_size = 5000
    for i in range(0, len(txns), batch_size):
        batch = txns[i : i + batch_size]
        await session.execute(insert(TransactionModel), batch)
    await session.commit()
    print(f"  Seeded {len(txns)} transactions")


async def seed(check_empty: bool = False) -> None:
    """Run the full seed process."""
    settings = DatabaseSettings()
    await init_engine(settings.cockroachdb_url, settings.pool_size)
    factory = get_session_factory()

    async with factory() as session:
        if check_empty and not await _is_empty(session):
            print("Database not empty — skipping seed (use without --check-empty to force)")
            return

        print("Seeding database...")
        await _seed_plans(session)
        accounts = await _seed_accounts(session)
        await _seed_transactions(session, accounts)
        print("Done!")

    await dispose_engine()


def main() -> None:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="Seed the CockroachDB database")
    parser.add_argument(
        "--check-empty",
        action="store_true",
        help="Only seed if the accounts table is empty",
    )
    args = parser.parse_args()
    asyncio.run(seed(check_empty=args.check_empty))


if __name__ == "__main__":
    main()
