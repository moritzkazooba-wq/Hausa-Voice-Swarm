"""Tests for Transaction and ActionResult models."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError
from src.models.transaction import ActionResult, Transaction


class TestTransaction:
    """Transaction validation tests."""

    def _valid_data(self) -> dict:  # type: ignore[type-arg]
        return {
            "id": uuid4(),
            "account_id": uuid4(),
            "amount": Decimal("5000.00"),
            "merchant": "MTN Airtime",
            "date": datetime.now(tz=UTC),
            "status": "completed",
            "type": "debit",
        }

    def test_valid_transaction(self) -> None:
        txn = Transaction(**self._valid_data())
        assert txn.status == "completed"
        assert txn.type == "debit"

    def test_invalid_status(self) -> None:
        data = self._valid_data()
        data["status"] = "cancelled"
        with pytest.raises(ValidationError):
            Transaction(**data)

    def test_invalid_type(self) -> None:
        data = self._valid_data()
        data["type"] = "refund"
        with pytest.raises(ValidationError):
            Transaction(**data)

    def test_serialization_roundtrip(self) -> None:
        txn = Transaction(**self._valid_data())
        json_str = txn.model_dump_json()
        restored = Transaction.model_validate_json(json_str)
        assert restored == txn

    def test_decimal_amount_precision(self) -> None:
        data = self._valid_data()
        data["amount"] = Decimal("12345.67")
        txn = Transaction(**data)
        json_str = txn.model_dump_json()
        restored = Transaction.model_validate_json(json_str)
        assert restored.amount == Decimal("12345.67")


class TestActionResult:
    """ActionResult validation tests."""

    def test_success_result(self) -> None:
        result = ActionResult(success=True, message="Transfer complete", reference_id="TXN-001")
        assert result.success is True
        assert result.reference_id == "TXN-001"
        assert result.requires_confirmation is False

    def test_reference_id_none(self) -> None:
        result = ActionResult(success=False, message="Failed")
        assert result.reference_id is None

    def test_reference_id_none_serialization(self) -> None:
        result = ActionResult(success=True, message="OK", reference_id=None)
        json_str = result.model_dump_json()
        restored = ActionResult.model_validate_json(json_str)
        assert restored.reference_id is None

    def test_requires_confirmation_default(self) -> None:
        result = ActionResult(success=True, message="OK")
        assert result.requires_confirmation is False

    def test_requires_confirmation_true(self) -> None:
        result = ActionResult(
            success=True,
            message="Confirm transfer of 5000 NGN?",
            requires_confirmation=True,
        )
        assert result.requires_confirmation is True

    def test_serialization_roundtrip(self) -> None:
        result = ActionResult(
            success=True,
            message="Done",
            reference_id="REF-42",
            requires_confirmation=True,
        )
        json_str = result.model_dump_json()
        restored = ActionResult.model_validate_json(json_str)
        assert restored == result
