from __future__ import annotations

from datetime import UTC, datetime

import pytest

from tlvflow.domain.enums import RideStatus
from tlvflow.domain.rides import Ride
from tlvflow.persistence.rides_repository import (
    RidesRepository,
    _ride_from_dict,
    _ride_to_dict,
)


def make_ride(*, user_id: str = "u1", vehicle_id: str = "v1") -> Ride:
    return Ride(
        user_id=user_id,
        vehicle_id=vehicle_id,
        start_time=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        start_latitude=32.1,
        start_longitude=34.8,
    )


def test_add_and_get_by_id_and_user_id() -> None:
    repo = RidesRepository()

    r1 = make_ride(user_id="u1", vehicle_id="v1")
    r2 = make_ride(user_id="u1", vehicle_id="v2")

    repo.add(r1)
    repo.add(r2)

    assert repo.get_by_id(r1.ride_id) is r1

    rides = repo.get_by_user_id("u1")
    assert rides == [r1, r2]


def test_get_by_id_invalid_inputs_return_none() -> None:
    repo = RidesRepository()

    assert repo.get_by_id("") is None
    assert repo.get_by_id("   ") is None
    assert repo.get_by_id(None) is None  # type: ignore[arg-type]
    assert repo.get_by_id(123) is None  # type: ignore[arg-type]


def test_get_by_user_id_invalid_inputs_return_empty_list() -> None:
    repo = RidesRepository()

    assert repo.get_by_user_id("") == []
    assert repo.get_by_user_id("   ") == []
    assert repo.get_by_user_id(None) == []  # type: ignore[arg-type]
    assert repo.get_by_user_id(123) == []  # type: ignore[arg-type]


def test_snapshot_and_restore_round_trip_preserves_order_and_status() -> None:
    repo = RidesRepository()

    active = make_ride(user_id="u1", vehicle_id="v1")

    cancelled = make_ride(user_id="u1", vehicle_id="v2")
    cancelled.cancel()

    completed = make_ride(user_id="u2", vehicle_id="v3")
    completed.end(datetime(2026, 1, 1, 12, 30, tzinfo=UTC))

    repo.add(active)
    repo.add(cancelled)
    repo.add(completed)

    snapshot = repo.snapshot()

    restored = RidesRepository()
    restored.restore(snapshot)

    r1 = restored.get_by_id(active.ride_id)
    assert r1 is not None
    assert r1.status() == RideStatus.ACTIVE

    r2 = restored.get_by_id(cancelled.ride_id)
    assert r2 is not None
    assert r2.status() == RideStatus.CANCELLED

    r3 = restored.get_by_id(completed.ride_id)
    assert r3 is not None
    assert r3.status() == RideStatus.COMPLETED

    assert [r.ride_id for r in restored.get_by_user_id("u1")] == [
        r1.ride_id,
        r2.ride_id,
    ]
    assert [r.ride_id for r in restored.get_by_user_id("u2")] == [r3.ride_id]


def test_restore_clears_previous_state() -> None:
    repo = RidesRepository()

    old_ride = make_ride(user_id="u1", vehicle_id="v1")
    repo.add(old_ride)
    new_ride = make_ride(user_id="u2", vehicle_id="v2")

    repo.restore({new_ride.ride_id: _ride_to_dict(new_ride)})

    assert repo.get_by_id(old_ride.ride_id) is None
    assert repo.get_by_user_id("u1") == []
    assert repo.get_by_id(new_ride.ride_id) is not None
    assert [r.ride_id for r in repo.get_by_user_id("u2")] == [new_ride.ride_id]


def test_ride_from_dict_cancelled_with_end_time_raises() -> None:
    data = _ride_to_dict(make_ride(user_id="u1", vehicle_id="v1"))
    data["status"] = RideStatus.CANCELLED.value
    data["end_time"] = datetime(2026, 1, 1, 13, 0, tzinfo=UTC).isoformat()

    with pytest.raises(ValueError):
        _ride_from_dict(data)
