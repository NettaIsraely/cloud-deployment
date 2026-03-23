"""Payment domain model: a record of a charge, receipt, or refund."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from tlvflow.domain.enums import PaymentKind


class Payment:
    """A single payment record (charge, receipt, or refund) for a ride."""

    _payment_id: str
    _ride_id: str
    _amount: float
    _payment_method_id: str
    _email: str | None
    _kind: PaymentKind
    _created_at: datetime

    def __init__(
        self,
        ride_id: str,
        amount: float,
        payment_method_id: str,
        kind: PaymentKind,
        *,
        payment_id: str | None = None,
        email: str | None = None,
        created_at: datetime | None = None,
    ) -> None:
        self._payment_id = payment_id or uuid4().hex
        self._ride_id = self._validate_ride_id(ride_id)
        self._amount = self._validate_amount(amount)
        self._payment_method_id = self._validate_payment_method_id(payment_method_id)
        self._email = (
            email.strip() if isinstance(email, str) and email.strip() else None
        )
        self._kind = kind
        self._created_at = created_at or datetime.now(UTC)

    @staticmethod
    def _validate_ride_id(ride_id: str) -> str:
        if not isinstance(ride_id, str) or not ride_id.strip():
            raise ValueError("ride_id must be a non-empty string")
        return ride_id.strip()

    @staticmethod
    def _validate_amount(amount: float) -> float:
        if not isinstance(amount, int | float) or amount <= 0:
            raise ValueError("amount must be a positive number")
        return float(amount)

    @staticmethod
    def _validate_payment_method_id(payment_method_id: str) -> str:
        if not isinstance(payment_method_id, str) or not payment_method_id.strip():
            raise ValueError("payment_method_id must be a non-empty string")
        return payment_method_id.strip()

    @property
    def payment_id(self) -> str:
        return self._payment_id

    @property
    def ride_id(self) -> str:
        return self._ride_id

    @property
    def amount(self) -> float:
        return self._amount

    @property
    def payment_method_id(self) -> str:
        return self._payment_method_id

    @property
    def email(self) -> str | None:
        return self._email

    @property
    def kind(self) -> PaymentKind:
        return self._kind

    @property
    def created_at(self) -> datetime:
        return self._created_at
