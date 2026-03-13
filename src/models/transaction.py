"""Transaction and action result models."""

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class Transaction(BaseModel):
    """Financial transaction record."""

    model_config = ConfigDict(strict=True)

    id: UUID
    account_id: UUID
    amount: Decimal
    merchant: str
    date: datetime
    status: Literal["completed", "pending", "failed"]
    type: Literal["credit", "debit"]


class ActionResult(BaseModel):
    """Result of an agent action (e.g. transfer, bill payment)."""

    model_config = ConfigDict(strict=True)

    success: bool
    message: str
    reference_id: str | None = None
    requires_confirmation: bool = False
