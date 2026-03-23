"""Additional tests for degraded_vehicles_repository and degraded_vehicles_service coverage."""

from __future__ import annotations

import asyncio

from tlvflow.domain.enums import VehicleStatus
from tlvflow.domain.stations import Station
from tlvflow.domain.vehicles import Bike
from tlvflow.persistence.degraded_vehicles_repository import DegradedVehiclesRepository
from tlvflow.persistence.in_memory import StationRepository, VehicleRepository
from tlvflow.services.degraded_vehicles_service import mark_degraded, restore_degraded

# --- DegradedVehiclesRepository ---


def test_get_by_id_with_invalid_id() -> None:
    repo = DegradedVehiclesRepository()
    assert repo.get_by_id("") is None
    assert repo.get_by_id("   ") is None


def test_restore_with_invalid_vehicle_ids_type() -> None:
    repo = DegradedVehiclesRepository()
    vehicle_repo = VehicleRepository()
    repo.restore({"vehicle_ids": "not-a-list"}, vehicle_repo=vehicle_repo)
    assert repo.get_all() == []


def test_restore_skips_invalid_entries() -> None:
    repo = DegradedVehiclesRepository()
    vehicle_repo = VehicleRepository()
    bike = Bike("v1", "F1")
    vehicle_repo.add(bike)
    repo.restore({"vehicle_ids": ["", "   ", "v1", None]}, vehicle_repo=vehicle_repo)
    assert len(repo.get_all()) == 1


def test_restore_skips_missing_vehicles() -> None:
    repo = DegradedVehiclesRepository()
    vehicle_repo = VehicleRepository()
    repo.restore({"vehicle_ids": ["v_missing"]}, vehicle_repo=vehicle_repo)
    assert repo.get_all() == []


# --- mark_degraded edge cases ---


def test_mark_degraded_empty_vehicle_id() -> None:
    vehicle_repo = VehicleRepository()
    station_repo = StationRepository()
    degraded_repo = DegradedVehiclesRepository()

    result = asyncio.run(mark_degraded(station_repo, vehicle_repo, degraded_repo, ""))
    assert result is None


def test_mark_degraded_vehicle_not_found() -> None:
    vehicle_repo = VehicleRepository()
    station_repo = StationRepository()
    degraded_repo = DegradedVehiclesRepository()

    result = asyncio.run(
        mark_degraded(station_repo, vehicle_repo, degraded_repo, "nonexistent")
    )
    assert result is None


def test_mark_degraded_station_not_found() -> None:
    vehicle_repo = VehicleRepository()
    station_repo = StationRepository()
    degraded_repo = DegradedVehiclesRepository()

    bike = Bike("v1", "F1")
    bike._station_id = 999
    vehicle_repo.add(bike)

    result = asyncio.run(mark_degraded(station_repo, vehicle_repo, degraded_repo, "v1"))
    assert result is None


# --- restore_degraded: vehicle not at station (no undock needed) ---


def test_restore_degraded_vehicle_not_at_station() -> None:
    """Vehicle in degraded set has no station_id -- skip undock."""
    vehicle_repo = VehicleRepository()
    station_repo = StationRepository()
    degraded_repo = DegradedVehiclesRepository()

    bike = Bike("v1", "F1", status=VehicleStatus.DEGRADED)
    vehicle_repo.add(bike)

    asyncio.run(
        restore_degraded(
            station_repo, vehicle_repo, degraded_repo, {"vehicle_ids": ["v1"]}
        )
    )
    assert len(degraded_repo.get_all()) == 1
    assert bike.station_id is None


def test_restore_degraded_vehicle_at_station_but_not_in_vehicles_list() -> None:
    """Vehicle has station_id but isn't in station.vehicles -- skip undock."""
    vehicle_repo = VehicleRepository()
    station_repo = StationRepository()
    degraded_repo = DegradedVehiclesRepository()

    bike = Bike("v1", "F1", status=VehicleStatus.DEGRADED)
    bike._station_id = 1
    vehicle_repo.add(bike)
    station = Station(
        station_id=1, name="S1", latitude=32.0, longitude=34.0, capacity=5
    )
    station_repo.add(station)

    asyncio.run(
        restore_degraded(
            station_repo, vehicle_repo, degraded_repo, {"vehicle_ids": ["v1"]}
        )
    )
    assert len(degraded_repo.get_all()) == 1
