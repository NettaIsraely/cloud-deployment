"""Unit tests for vehicles_service: report_degraded_vehicle."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from tlvflow.domain.enums import VehicleStatus
from tlvflow.domain.rides import Ride
from tlvflow.domain.vehicles import Bike
from tlvflow.persistence.active_users_repository import ActiveUsersRepository
from tlvflow.persistence.degraded_vehicles_repository import DegradedVehiclesRepository
from tlvflow.persistence.in_memory import VehicleRepository
from tlvflow.persistence.rides_repository import RidesRepository
from tlvflow.services.vehicles_service import report_degraded_vehicle


def _make_bike(vid: str) -> Bike:
    return Bike(vehicle_id=vid, frame_number=f"F-{vid}", status=VehicleStatus.AVAILABLE)


# --- report during active ride ---


async def test_report_degraded_during_active_ride() -> None:
    rides_repo = RidesRepository()
    vehicles_repo = VehicleRepository()
    degraded_repo = DegradedVehiclesRepository()
    active_repo = ActiveUsersRepository()

    bike = _make_bike("v1")
    vehicles_repo.add(bike)

    ride = Ride(user_id="u1", vehicle_id="v1", start_time=datetime.now(UTC))
    rides_repo.add(ride)
    active_repo.set_active("u1", ride.ride_id)

    await report_degraded_vehicle(
        user_id="u1",
        vehicle_id="v1",
        rides_repo=rides_repo,
        vehicles_repo=vehicles_repo,
        degraded_repo=degraded_repo,
        active_users_repo=active_repo,
    )

    assert ride.end_time is not None
    assert ride.fee == 0.0
    assert active_repo.get_ride_id("u1") is None
    assert len(degraded_repo.get_all()) == 1
    assert vehicles_repo.get_by_id("v1") is None


async def test_report_degraded_vehicle_not_found_during_active_ride() -> None:
    rides_repo = RidesRepository()
    vehicles_repo = VehicleRepository()
    degraded_repo = DegradedVehiclesRepository()
    active_repo = ActiveUsersRepository()

    ride = Ride(user_id="u1", vehicle_id="v_missing", start_time=datetime.now(UTC))
    rides_repo.add(ride)
    active_repo.set_active("u1", ride.ride_id)

    with pytest.raises(LookupError, match="vehicle not found"):
        await report_degraded_vehicle(
            user_id="u1",
            vehicle_id="v_missing",
            rides_repo=rides_repo,
            vehicles_repo=vehicles_repo,
            degraded_repo=degraded_repo,
            active_users_repo=active_repo,
        )


async def test_report_degraded_no_active_ride_raises() -> None:
    rides_repo = RidesRepository()
    vehicles_repo = VehicleRepository()
    degraded_repo = DegradedVehiclesRepository()
    active_repo = ActiveUsersRepository()

    with pytest.raises(ValueError, match="no active ride"):
        await report_degraded_vehicle(
            user_id="u1",
            vehicle_id="v1",
            rides_repo=rides_repo,
            vehicles_repo=vehicles_repo,
            degraded_repo=degraded_repo,
            active_users_repo=active_repo,
        )


async def test_report_degraded_wrong_vehicle_no_active_ride_raises() -> None:
    """Reporting a vehicle that is not the current ride vehicle raises."""
    rides_repo = RidesRepository()
    vehicles_repo = VehicleRepository()
    degraded_repo = DegradedVehiclesRepository()
    active_repo = ActiveUsersRepository()

    ride = Ride(user_id="u1", vehicle_id="v_other", start_time=datetime.now(UTC))
    rides_repo.add(ride)
    active_repo.set_active("u1", ride.ride_id)

    with pytest.raises(ValueError, match="no active ride"):
        await report_degraded_vehicle(
            user_id="u1",
            vehicle_id="v_wrong",
            rides_repo=rides_repo,
            vehicles_repo=vehicles_repo,
            degraded_repo=degraded_repo,
            active_users_repo=active_repo,
        )
