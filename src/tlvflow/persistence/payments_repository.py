"""In-memory repository for payments, with snapshot/restore for persistence."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from tlvflow.domain.enums import PaymentKind
from tlvflow.domain.payment import Payment


class PaymentsRepository:
    """In-memory repository for payments, with snapshot/restore for persistence."""

    def __init__(self) -> None:
        self._payments_by_id: dict[str, Payment] = {}
        self._payment_ids_by_ride_id: dict[str, list[str]] = {}

    def get_by_id(self, payment_id: str) -> Payment | None:
        if not isinstance(payment_id, str) or not payment_id.strip():
            return None
        return self._payments_by_id.get(payment_id.strip())

    def get_by_ride_id(self, ride_id: str) -> list[Payment]:
        if not isinstance(ride_id, str) or not ride_id.strip():
            return []
        ids = self._payment_ids_by_ride_id.get(ride_id.strip(), [])
        return [self._payments_by_id[pid] for pid in ids if pid in self._payments_by_id]

    def add(self, payment: Payment) -> None:
        self._payments_by_id[payment.payment_id] = payment
        self._payment_ids_by_ride_id.setdefault(payment.ride_id, []).append(
            payment.payment_id
        )

    def snapshot(self) -> dict[str, Any]:
        return {
            payment_id: _payment_to_dict(p)
            for payment_id, p in self._payments_by_id.items()
        }

    def restore(self, snapshot: dict[str, Any]) -> None:
        self._payments_by_id.clear()
        self._payment_ids_by_ride_id.clear()

        for payment_id, raw in snapshot.items():
            payment = _payment_from_dict(raw)
            self._payments_by_id[payment_id] = payment
            self._payment_ids_by_ride_id.setdefault(payment.ride_id, []).append(
                payment.payment_id
            )


def _payment_to_dict(payment: Payment) -> dict[str, Any]:
    return {
        "payment_id": payment.payment_id,
        "ride_id": payment.ride_id,
        "amount": payment.amount,
        "payment_method_id": payment.payment_method_id,
        "email": payment.email,
        "kind": payment.kind.value,
        "created_at": payment.created_at.isoformat(),
    }


def _payment_from_dict(data: dict[str, Any]) -> Payment:
    payment_id = str(data["payment_id"])
    ride_id = str(data["ride_id"])
    amount = float(data["amount"])
    payment_method_id = str(data["payment_method_id"])
    kind = PaymentKind(str(data["kind"]))
    email_raw = data.get("email")
    email = (str(email_raw).strip() or None) if email_raw is not None else None
    created_at_raw = data.get("created_at")
    created_at = datetime.fromisoformat(str(created_at_raw)) if created_at_raw else None

    return Payment(
        ride_id=ride_id,
        amount=amount,
        payment_method_id=payment_method_id,
        kind=kind,
        payment_id=payment_id,
        email=email,
        created_at=created_at,
    )
