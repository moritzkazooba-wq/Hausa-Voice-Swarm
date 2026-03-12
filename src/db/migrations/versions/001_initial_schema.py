"""Initial schema: accounts, transactions, plans.

Revision ID: 001
Revises:
Create Date: 2026-03-12
"""

import contextlib
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- accounts ---
    op.create_table(
        "accounts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("phone_number", sa.String(15), unique=True, nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("balance", sa.Numeric(14, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="NGN"),
        sa.Column("plan", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("region", sa.String(50), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_accounts_phone_number", "accounts", ["phone_number"])

    # Locality clauses: CockroachDB-specific, silently skip on Postgres
    with contextlib.suppress(Exception):
        op.execute("ALTER TABLE accounts SET LOCALITY REGIONAL BY ROW")

    # --- transactions ---
    op.create_table(
        "transactions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "account_id",
            sa.Uuid(),
            sa.ForeignKey("accounts.id"),
            nullable=False,
        ),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("merchant", sa.String(200), nullable=False),
        sa.Column("type", sa.String(10), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_transactions_account_id", "transactions", ["account_id"])

    with contextlib.suppress(Exception):
        op.execute("ALTER TABLE transactions SET LOCALITY REGIONAL BY ROW")

    # --- plans ---
    op.create_table(
        "plans",
        sa.Column("name", sa.String(50), primary_key=True),
        sa.Column("monthly_fee", sa.Numeric(10, 2), nullable=False),
        sa.Column("data_gb", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(500), nullable=False),
    )

    with contextlib.suppress(Exception):
        op.execute("ALTER TABLE plans SET LOCALITY GLOBAL")


def downgrade() -> None:
    op.drop_table("plans")
    op.drop_table("transactions")
    op.drop_table("accounts")
