"""Customer and network models."""

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CustomerProfile(BaseModel):
    """Mobile money customer profile."""

    model_config = ConfigDict(strict=True)

    id: UUID
    phone_number: str = Field(pattern=r"^\+234\d{10}$")
    name: str
    balance: Decimal = Field(max_digits=12, decimal_places=2)
    currency: str = "NGN"
    plan: str
    status: str
    region: str


class NetworkStatus(BaseModel):
    """Regional network health status."""

    model_config = ConfigDict(strict=True)

    region: str
    status: Literal["healthy", "degraded", "down"]
    latency_ms: float
    last_checked: datetime
