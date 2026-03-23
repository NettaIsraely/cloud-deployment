"""Unit tests for degraded_vehicles_service."""

from __future__ import annotations

import asyncio

import pytest

from tlvflow.domain.enums import VehicleStatus
from tlvflow.domain.stations import Station
from tlvflow.domain.vehicles import Bike
from tlvflow.persistence.degraded_vehicles_repository import (
    DegradedVehiclesRepository,
)
from tlvflow.persistence.in_memory import StationRepository, VehicleRepository
from tlvflow.services.degraded_vehicles_service import (
    mark_degraded,
    restore_degraded,
    unmark_degraded,
)


def test_mark_degraded_undocks_and_adds_to_repo() -> None:
    vehicle_repo = VehicleRepository()
    station_repo = StationRepository()
    degraded_repo = DegradedVehiclesRepository()

    bike = Bike("v1", "F1", status=VehicleStatus.DEGRADED)
    vehicle_repo.add(bike)
    station = Station(1, "Central", 32.0, 34.8, capacity=5)
    station.dock(bike)
    station_repo.add(station)

    assert bike.station_id == 1
    out = asyncio.run(mark_degraded(station_repo, vehicle_repo, degraded_repo, "v1"))

    assert out is bike
    assert station.vehicles == ()
    assert bike.station_id is None
    assert degraded_repo.get_all() == [bike]


def test_mark_degraded_returns_none_when_vehicle_not_at_station() -> None:
    vehicle_repo = VehicleRepository()
    station_repo = StationRepository()
    degraded_repo = DegradedVehiclesRepository()
    bike = Bike("v1", "F1", status=VehicleStatus.DEGRADED)
    vehicle_repo.add(bike)

    assert (
        asyncio.run(mark_degraded(station_repo, vehicle_repo, degraded_repo, "v1"))
        is None
    )
    assert degraded_repo.get_all() == []


def test_unmark_degraded_docks_at_random_station() -> None:
    vehicle_repo = VehicleRepository()
    station_repo = StationRepository()
    degraded_repo = DegradedVehiclesRepository()
    bike = Bike("v1", "F1", status=VehicleStatus.DEGRADED)
    vehicle_repo.add(bike)
    degraded_repo.add(bike)
    station = Station(1, "Central", 32.0, 34.8, capacity=5)
    station_repo.add(station)

    out = asyncio.run(unmark_degraded(station_repo, degraded_repo, "v1"))

    assert out is bike
    assert degraded_repo.get_all() == []
    assert len(station.vehicles) == 1 and station.vehicles[0] is bike
    assert bike.station_id == 1


def test_unmark_degraded_when_no_capacity_raises() -> None:
    vehicle_repo = VehicleRepository()
    station_repo = StationRepository()
    degraded_repo = DegradedVehiclesRepository()
    bike1 = Bike("v1", "F1", status=VehicleStatus.DEGRADED)
    bike2 = Bike("v2", "F2", status=VehicleStatus.AVAILABLE)
    bike3 = Bike("v3", "F3", status=VehicleStatus.AVAILABLE)
    vehicle_repo.add(bike1)
    vehicle_repo.add(bike2)
    vehicle_repo.add(bike3)
    degraded_repo.add(bike1)
    s1 = Station(1, "A", 32.0, 34.8, capacity=1)
    s2 = Station(2, "B", 32.1, 34.9, capacity=1)
    s1.dock(bike2)
    s2.dock(bike3)
    station_repo.add(s1)
    station_repo.add(s2)

    with pytest.raises(ValueError, match="No station with available capacity"):
        asyncio.run(unmark_degraded(station_repo, degraded_repo, "v1"))

    assert degraded_repo.get_by_id("v1") is bike1


def test_restore_degraded_undocks_vehicles_from_stations() -> None:
    vehicle_repo = VehicleRepository()
    station_repo = StationRepository()
    degraded_repo = DegradedVehiclesRepository()
    bike = Bike("v1", "F1", status=VehicleStatus.DEGRADED)
    vehicle_repo.add(bike)
    station = Station(1, "Central", 32.0, 34.8, capacity=5)
    station.dock(bike)
    station_repo.add(station)

    asyncio.run(
        restore_degraded(
            station_repo,
            vehicle_repo,
            degraded_repo,
            {"vehicle_ids": ["v1"]},
        )
    )

    assert len(degraded_repo.get_all()) == 1
    assert degraded_repo.get_by_id("v1") is bike
    assert station.vehicles == ()
    assert bike.station_id is None
