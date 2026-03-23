"""Unit tests for link_vehicles_to_stations."""

import asyncio
import logging

import pytest

from tlvflow.domain.enums import VehicleStatus
from tlvflow.domain.stations import Station
from tlvflow.domain.vehicles import Bike
from tlvflow.persistence.degraded_vehicles_repository import (
    DegradedVehiclesRepository,
)
from tlvflow.persistence.in_memory import StationRepository, VehicleRepository
from tlvflow.services.link_vehicles import link_vehicles_to_stations


def test_link_docks_vehicle_at_station_by_station_id() -> None:
    vehicle_repo = VehicleRepository()
    station_repo = StationRepository()
    degraded_repo = DegradedVehiclesRepository()

    bike = Bike(
        vehicle_id="v1",
        frame_number="F-1",
        status=VehicleStatus.AVAILABLE,
    )
    bike._station_id = 1
    vehicle_repo.add(bike)

    station = Station(
        station_id=1,
        name="Central",
        latitude=32.0,
        longitude=34.0,
        capacity=2,
    )
    station_repo.add(station)

    asyncio.run(link_vehicles_to_stations(vehicle_repo, station_repo, degraded_repo))

    assert station_repo.get_by_id(1) is not None
    assert [v._vehicle_id for v in station_repo.get_by_id(1).vehicles] == ["v1"]
    assert bike.station_id == 1
    assert list(degraded_repo.get_all()) == []


def test_link_degraded_vehicle_goes_to_degraded_repo_not_docked() -> None:
    vehicle_repo = VehicleRepository()
    station_repo = StationRepository()
    degraded_repo = DegradedVehiclesRepository()

    bike = Bike(
        vehicle_id="v2",
        frame_number="F-2",
        status=VehicleStatus.DEGRADED,
    )
    bike._station_id = 1
    vehicle_repo.add(bike)

    station = Station(
        station_id=1,
        name="Central",
        latitude=32.0,
        longitude=34.0,
        capacity=2,
    )
    station_repo.add(station)

    asyncio.run(link_vehicles_to_stations(vehicle_repo, station_repo, degraded_repo))

    assert list(station_repo.get_by_id(1).vehicles) == []
    assert list(degraded_repo.get_all()) == [bike]


def test_link_station_not_found_logs_and_skips(
    caplog: pytest.LogCaptureFixture,
) -> None:
    vehicle_repo = VehicleRepository()
    station_repo = StationRepository()
    degraded_repo = DegradedVehiclesRepository()

    bike = Bike(
        vehicle_id="v3",
        frame_number="F-3",
        status=VehicleStatus.AVAILABLE,
    )
    bike._station_id = 999
    vehicle_repo.add(bike)

    with caplog.at_level(logging.WARNING):
        asyncio.run(
            link_vehicles_to_stations(vehicle_repo, station_repo, degraded_repo)
        )

    assert "Station 999 not found" in caplog.text
    assert bike.station_id == 999
    assert list(degraded_repo.get_all()) == []


def test_link_station_full_logs_and_skips(caplog: pytest.LogCaptureFixture) -> None:
    vehicle_repo = VehicleRepository()
    station_repo = StationRepository()
    degraded_repo = DegradedVehiclesRepository()

    bike1 = Bike(
        vehicle_id="v4a",
        frame_number="F-4a",
        status=VehicleStatus.AVAILABLE,
    )
    bike1._station_id = 1
    bike2 = Bike(
        vehicle_id="v4b",
        frame_number="F-4b",
        status=VehicleStatus.AVAILABLE,
    )
    bike2._station_id = 1
    vehicle_repo.add(bike1)
    vehicle_repo.add(bike2)

    station = Station(
        station_id=1,
        name="Small",
        latitude=32.0,
        longitude=34.0,
        capacity=1,
    )
    station_repo.add(station)

    with caplog.at_level(logging.WARNING):
        asyncio.run(
            link_vehicles_to_stations(vehicle_repo, station_repo, degraded_repo)
        )

    assert "Station 1 is full" in caplog.text
    docked = list(station_repo.get_by_id(1).vehicles)
    assert len(docked) == 1
    assert docked[0]._vehicle_id in ("v4a", "v4b")


def test_link_no_station_id_logs_and_skips(caplog: pytest.LogCaptureFixture) -> None:
    vehicle_repo = VehicleRepository()
    station_repo = StationRepository()
    degraded_repo = DegradedVehiclesRepository()

    bike = Bike(
        vehicle_id="v5",
        frame_number="F-5",
        status=VehicleStatus.AVAILABLE,
    )
    assert bike.station_id is None
    vehicle_repo.add(bike)

    with caplog.at_level(logging.WARNING):
        asyncio.run(
            link_vehicles_to_stations(vehicle_repo, station_repo, degraded_repo)
        )

    assert "no station_id" in caplog.text
    assert list(degraded_repo.get_all()) == []
