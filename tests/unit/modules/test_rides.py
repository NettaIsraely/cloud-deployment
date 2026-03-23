"""
Unit tests for tlvflow.domain.rides (Ride model).
"""

from __future__ import annotations

import re
from datetime import UTC, datetime

import pytest

from tlvflow.domain.enums import RideStatus
from tlvflow.domain.rides import Ride


def make_ride(
    *,
    user_id: str = "u1",
    vehicle_id: str = "v1",
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    fee: float = 0.0,
    **kwargs: object,
) -> Ride:
    start = start_time or datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    return Ride(
        user_id=user_id,
        vehicle_id=vehicle_id,
        start_time=start,
        end_time=end_time,
        fee=fee,
        **kwargs,
    )


# --- Ride creation ---


def test_ride_creation_minimal() -> None:
    """Ride with only required fields has ACTIVE status and default location/fee."""
    r = make_ride()
    assert len(r.ride_id) == 32
    assert re.fullmatch(r"[0-9a-f]{32}", r.ride_id) is not None
    assert r.user_id == "u1"
    assert r.vehicle_id == "v1"
    assert r.start_time.tzinfo is not None
    assert r.end_time is None
    assert r.start_latitude == 0.0
    assert r.start_longitude == 0.0
    assert r.distance == 0.0
    assert r.fee == 0.0
    assert r.status() == RideStatus.ACTIVE
    assert r.is_active() is True


def test_ride_creation_with_end_time_is_completed() -> None:
    """Ride created with end_time is COMPLETED."""
    start = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    end = datetime(2026, 1, 1, 12, 30, tzinfo=UTC)
    r = make_ride(start_time=start, end_time=end)
    assert r.status() == RideStatus.COMPLETED
    assert r.is_active() is False
    assert r.end_time == end


def test_ride_creation_strips_ids() -> None:
    """user_id, vehicle_id are stripped of surrounding whitespace."""
    r = Ride(
        user_id="  usr-1  ",
        vehicle_id="  v-1  ",
        start_time=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
    )
    assert r.user_id == "usr-1"
    assert r.vehicle_id == "v-1"


def test_ride_creation_with_all_optionals() -> None:
    """Ride accepts optional location, distance, fee."""
    start = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    r = Ride(
        user_id="u1",
        vehicle_id="v1",
        start_time=start,
        start_latitude=32.0,
        start_longitude=34.0,
        end_latitude=32.1,
        end_longitude=34.1,
        distance=5.5,
        fee=10.0,
    )
    assert r.start_latitude == 32.0
    assert r.start_longitude == 34.0
    assert r.end_latitude == 32.1
    assert r.end_longitude == 34.1
    assert r.distance == 5.5
    assert r.fee == 10.0


# --- Ending a ride ---


def test_ride_end_sets_completed_and_end_time() -> None:
    """end() sets status to COMPLETED and sets end_time."""
    start = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    end = datetime(2026, 1, 1, 12, 20, tzinfo=UTC)
    r = make_ride(start_time=start)
    assert r.is_active() is True

    r.end(at=end)
    assert r.status() == RideStatus.COMPLETED
    assert r.end_time == end
    assert r.is_active() is False


def test_ride_end_uses_now_when_at_not_given() -> None:
    """end() without at uses current time (UTC)."""
    r = make_ride()
    r.end()
    assert r.status() == RideStatus.COMPLETED
    assert r.end_time is not None
    assert r.end_time.tzinfo is not None


def test_ride_end_rejects_end_before_start() -> None:
    """end(at=...) raises when at is before start_time."""
    start = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    before = datetime(2026, 1, 1, 11, 0, tzinfo=UTC)
    r = make_ride(start_time=start)
    with pytest.raises(ValueError, match="end_time cannot be before start_time"):
        r.end(at=before)


# --- Degraded (payment=0) ---


def test_ride_degraded_payment_zero() -> None:
    """Completed ride with fee=0 is valid (degraded / no payment)."""
    r = make_ride(fee=0.0)
    assert r.fee == 0.0
    r.end(at=datetime(2026, 1, 1, 12, 10, tzinfo=UTC))
    assert r.status() == RideStatus.COMPLETED
    assert r.fee == 0.0


def test_ride_set_fee_for_degraded() -> None:
    """set_fee(0) explicitly sets fee to 0 (e.g. degraded report = free ride)."""
    r = make_ride()
    r.calculate_fee(duration=5.0, distance=2.0)
    assert r.fee == 15.0
    r.set_fee(0.0)
    assert r.fee == 0.0


def test_ride_created_completed_with_fee_zero() -> None:
    """Ride created already ended with fee=0 (degraded) has COMPLETED status."""
    start = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    end = datetime(2026, 1, 1, 12, 5, tzinfo=UTC)
    r = make_ride(start_time=start, end_time=end, fee=0.0)
    assert r.status() == RideStatus.COMPLETED
    assert r.fee == 0.0


# --- Edge cases: already ended ---


def test_ride_end_already_ended_raises() -> None:
    """end() on an already ended ride raises."""
    start = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    end = datetime(2026, 1, 1, 12, 10, tzinfo=UTC)
    r = make_ride(start_time=start, end_time=end)
    with pytest.raises(ValueError, match="Ride is already ended"):
        r.end(at=datetime(2026, 1, 1, 12, 20, tzinfo=UTC))


def test_ride_end_after_calling_end_raises() -> None:
    """Calling end() twice on same ride raises on second call."""
    r = make_ride()
    r.end(at=datetime(2026, 1, 1, 12, 10, tzinfo=UTC))
    with pytest.raises(ValueError, match="Ride is already ended"):
        r.end(at=datetime(2026, 1, 1, 12, 20, tzinfo=UTC))


# --- Cancel ---


def test_ride_cancel_sets_cancelled() -> None:
    """cancel() sets status to CANCELLED."""
    r = make_ride()
    r.cancel()
    assert r.status() == RideStatus.CANCELLED
    assert r.is_active() is False


def test_ride_cancel_already_ended_raises() -> None:
    """cancel() on an already ended (completed) ride raises."""
    r = make_ride(
        start_time=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        end_time=datetime(2026, 1, 1, 12, 10, tzinfo=UTC),
    )
    with pytest.raises(ValueError, match="Ride is already ended"):
        r.cancel()


def test_ride_cancel_already_cancelled_raises() -> None:
    """cancel() when already CANCELLED raises."""
    r = make_ride()
    r.cancel()
    with pytest.raises(ValueError, match="Ride is already cancelled"):
        r.cancel()


# --- Missing / invalid fields (creation) ---


@pytest.mark.parametrize(
    ("user_id", "msg"),
    [
        ("", "user_id must be a non-empty string"),
        ("   ", "user_id must be a non-empty string"),
    ],
)
def test_ride_creation_invalid_user_id(user_id: str, msg: str) -> None:
    """Creation rejects empty or whitespace user_id."""
    with pytest.raises(ValueError, match=msg):
        Ride(
            user_id=user_id,
            vehicle_id="v1",
            start_time=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        )


@pytest.mark.parametrize(
    ("vehicle_id", "msg"),
    [
        ("", "vehicle_id must be a non-empty string"),
        ("   ", "vehicle_id must be a non-empty string"),
    ],
)
def test_ride_creation_invalid_vehicle_id(vehicle_id: str, msg: str) -> None:
    """Creation rejects empty or whitespace vehicle_id."""
    with pytest.raises(ValueError, match=msg):
        Ride(
            user_id="u1",
            vehicle_id=vehicle_id,
            start_time=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        )


def test_ride_creation_invalid_start_time_type() -> None:
    """Creation rejects non-datetime start_time."""
    with pytest.raises(ValueError, match="start_time must be a datetime"):
        Ride(
            user_id="u1",
            vehicle_id="v1",
            start_time="2026-01-01 12:00:00",  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    ("value", "name"),
    [
        ("not a number", "start_latitude"),
        (None, "start_latitude"),  # type: ignore[arg-type]
    ],
)
def test_ride_creation_invalid_float_field(value: object, name: str) -> None:
    """Creation rejects non-numeric values for float fields."""
    with pytest.raises(ValueError, match=f"{name} must be a number"):
        Ride(
            user_id="u1",
            vehicle_id="v1",
            start_time=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
            start_latitude=value,  # type: ignore[arg-type]
        )


# --- Helpers ---


def test_ride_calculate_fee_updates_fee_and_distance() -> None:
    """calculate_fee sets fee to constant 15.0 ILS per ride (PDF spec)."""
    r = make_ride()
    fee = r.calculate_fee(duration=10.0, distance=2.0)
    assert r.distance == 2.0
    assert r.fee == fee
    assert fee == 15.0


def test_ride_status_and_is_active() -> None:
    """status() and is_active() reflect ACTIVE / COMPLETED / CANCELLED."""
    r = make_ride()
    assert r.status() == RideStatus.ACTIVE
    assert r.is_active() is True

    r.end(at=datetime(2026, 1, 1, 12, 10, tzinfo=UTC))
    assert r.status() == RideStatus.COMPLETED
    assert r.is_active() is False

    r2 = make_ride()
    r2.cancel()
    assert r2.status() == RideStatus.CANCELLED
    assert r2.is_active() is False
