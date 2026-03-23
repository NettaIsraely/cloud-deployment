"""Unit tests for PaymentsRepository."""

from __future__ import annotations

from tlvflow.domain.enums import PaymentKind
from tlvflow.domain.payment import Payment
from tlvflow.persistence.payments_repository import (
    PaymentsRepository,
    _payment_from_dict,
    _payment_to_dict,
)


def make_payment(
    *,
    ride_id: str = "r1",
    amount: float = 10.5,
    payment_method_id: str = "pm_1",
    kind: PaymentKind = PaymentKind.CHARGE,
    payment_id: str | None = None,
    email: str | None = None,
) -> Payment:
    return Payment(
        ride_id=ride_id,
        amount=amount,
        payment_method_id=payment_method_id,
        kind=kind,
        payment_id=payment_id,
        email=email,
    )


def test_add_and_get_by_id_and_ride_id() -> None:
    repo = PaymentsRepository()

    p1 = make_payment(payment_id="pay1", ride_id="r1", amount=5.0)
    p2 = make_payment(payment_id="pay2", ride_id="r1", amount=3.0)
    p3 = make_payment(payment_id="pay3", ride_id="r2", amount=7.0)

    repo.add(p1)
    repo.add(p2)
    repo.add(p3)

    assert repo.get_by_id("pay1") is p1
    assert repo.get_by_id("  pay1  ") is p1

    by_r1 = repo.get_by_ride_id("r1")
    assert len(by_r1) == 2
    assert set(p.payment_id for p in by_r1) == {"pay1", "pay2"}

    by_r2 = repo.get_by_ride_id("r2")
    assert by_r2 == [p3]


def test_get_by_id_invalid_inputs_return_none() -> None:
    repo = PaymentsRepository()
    assert repo.get_by_id("") is None
    assert repo.get_by_id("   ") is None
    assert repo.get_by_id(None) is None  # type: ignore[arg-type]


def test_get_by_ride_id_invalid_inputs_return_empty_list() -> None:
    repo = PaymentsRepository()
    assert repo.get_by_ride_id("") == []
    assert repo.get_by_ride_id("   ") == []
    assert repo.get_by_ride_id(None) == []  # type: ignore[arg-type]


def test_snapshot_and_restore_round_trip() -> None:
    repo = PaymentsRepository()
    p1 = make_payment(
        payment_id="p1",
        ride_id="r1",
        amount=10.0,
        email="u@example.com",
        kind=PaymentKind.RECEIPT,
    )
    p2 = make_payment(
        payment_id="p2", ride_id="r2", amount=5.0, kind=PaymentKind.REFUND
    )
    repo.add(p1)
    repo.add(p2)

    snapshot = repo.snapshot()
    restored = PaymentsRepository()
    restored.restore(snapshot)

    r1 = restored.get_by_id("p1")
    assert r1 is not None
    assert r1.ride_id == "r1"
    assert r1.amount == 10.0
    assert r1.email == "u@example.com"
    assert r1.kind == PaymentKind.RECEIPT

    assert restored.get_by_ride_id("r1") == [r1]
    assert len(restored.get_by_ride_id("r2")) == 1


def test_payment_to_dict_and_from_dict_round_trip() -> None:
    p = make_payment(
        payment_id="id1",
        ride_id="r1",
        amount=99.99,
        payment_method_id="pm_x",
        email="a@b.co",
        kind=PaymentKind.CHARGE,
    )
    data = _payment_to_dict(p)
    assert data["payment_id"] == "id1"
    assert data["ride_id"] == "r1"
    assert data["amount"] == 99.99
    assert data["email"] == "a@b.co"
    assert data["kind"] == "charge"

    back = _payment_from_dict(data)
    assert back.payment_id == p.payment_id
    assert back.ride_id == p.ride_id
    assert back.amount == p.amount
    assert back.kind == p.kind
