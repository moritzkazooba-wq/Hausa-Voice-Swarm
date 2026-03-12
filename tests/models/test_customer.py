"""Tests for CustomerProfile and NetworkStatus models."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError
from src.models.customer import CustomerProfile, NetworkStatus


class TestCustomerProfile:
    """CustomerProfile validation tests."""

    def _valid_data(self) -> dict:  # type: ignore[type-arg]
        return {
            "id": uuid4(),
            "phone_number": "+2348012345678",
            "name": "Amina Bello",
            "balance": Decimal("15000.50"),
            "currency": "NGN",
            "plan": "basic",
            "status": "active",
            "region": "kano",
        }

    def test_valid_customer(self) -> None:
        data = self._valid_data()
        customer = CustomerProfile(**data)
        assert customer.phone_number == "+2348012345678"
        assert customer.balance == Decimal("15000.50")
        assert customer.currency == "NGN"

    def test_phone_regex_valid(self) -> None:
        data = self._valid_data()
        data["phone_number"] = "+2349087654321"
        customer = CustomerProfile(**data)
        assert customer.phone_number == "+2349087654321"

    def test_phone_regex_rejects_us_number(self) -> None:
        data = self._valid_data()
        data["phone_number"] = "+1234567890"
        with pytest.raises(ValidationError):
            CustomerProfile(**data)

    def test_phone_regex_rejects_alpha(self) -> None:
        data = self._valid_data()
        data["phone_number"] = "abc"
        with pytest.raises(ValidationError):
            CustomerProfile(**data)

    def test_phone_regex_rejects_empty(self) -> None:
        data = self._valid_data()
        data["phone_number"] = ""
        with pytest.raises(ValidationError):
            CustomerProfile(**data)

    def test_phone_regex_rejects_short(self) -> None:
        data = self._valid_data()
        data["phone_number"] = "+23480123"
        with pytest.raises(ValidationError):
            CustomerProfile(**data)

    def test_decimal_precision_roundtrip(self) -> None:
        data = self._valid_data()
        data["balance"] = Decimal("99999.99")
        customer = CustomerProfile(**data)
        json_str = customer.model_dump_json()
        restored = CustomerProfile.model_validate_json(json_str)
        assert restored.balance == Decimal("99999.99")

    def test_serialization_roundtrip(self) -> None:
        data = self._valid_data()
        customer = CustomerProfile(**data)
        json_str = customer.model_dump_json()
        restored = CustomerProfile.model_validate_json(json_str)
        assert restored == customer

    def test_missing_required_field(self) -> None:
        with pytest.raises(ValidationError):
            CustomerProfile(
                id=uuid4(),
                phone_number="+2348012345678",
                name="Test",
                balance=Decimal("0"),
                # missing plan, status, region
            )


class TestNetworkStatus:
    """NetworkStatus validation tests."""

    def test_valid_network_status(self) -> None:
        ns = NetworkStatus(
            region="kano",
            status="healthy",
            latency_ms=12.5,
            last_checked=datetime.now(tz=UTC),
        )
        assert ns.status == "healthy"

    def test_invalid_status_literal(self) -> None:
        with pytest.raises(ValidationError):
            NetworkStatus(
                region="kano",
                status="unknown",  # type: ignore[arg-type]
                latency_ms=10.0,
                last_checked=datetime.now(tz=UTC),
            )

    def test_datetime_with_timezone(self) -> None:
        dt = datetime(2024, 6, 15, 10, 30, 0, tzinfo=UTC)
        ns = NetworkStatus(region="lagos", status="degraded", latency_ms=50.0, last_checked=dt)
        json_str = ns.model_dump_json()
        restored = NetworkStatus.model_validate_json(json_str)
        assert restored.last_checked == dt

    def test_datetime_naive(self) -> None:
        dt = datetime(2024, 6, 15, 10, 30, 0)
        ns = NetworkStatus(region="abuja", status="down", latency_ms=999.0, last_checked=dt)
        assert ns.last_checked == dt
