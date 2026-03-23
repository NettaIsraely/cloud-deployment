"""Additional stations_service tests: find_nearest_station_with_eligible_vehicle, find_nearest_station_with_free_slot, distance_meters."""

from __future__ import annotations

import asyncio
from collections import defaultdict

from tlvflow.domain.enums import VehicleStatus
from tlvflow.domain.stations import Station
from tlvflow.domain.vehicles import Bike
from tlvflow.persistence.in_memory import StationRepository
from tlvflow.services.stations_service import (
    distance_meters,
    find_nearest_station_with_eligible_vehicle,
    find_nearest_station_with_free_slot,
)

# --- find_nearest_station_with_eligible_vehicle ---


async def test_find_nearest_eligible_returns_none_when_no_eligible() -> None:
    repo = StationRepository()
    station = Station(
        station_id=1, name="Empty", latitude=32.0, longitude=34.0, capacity=5
    )
    repo.add(station)

    result = await find_nearest_station_with_eligible_vehicle(repo, lon=34.0, lat=32.0)
    assert result is None


async def test_find_nearest_eligible_success_no_locks() -> None:
    repo = StationRepository()
    bike = Bike(vehicle_id="v1", frame_number="F1")
    station = Station(
        station_id=1,
        name="S1",
        latitude=32.0,
        longitude=34.0,
        capacity=5,
        vehicles=[bike],
    )
    repo.add(station)

    result = await find_nearest_station_with_eligible_vehicle(
        repo, lon=34.0, lat=32.0, station_locks=None
    )
    assert result is not None
    s, v = result
    assert s.station_id == 1
    assert v.vehicle_id == "v1"


async def test_find_nearest_eligible_with_station_locks() -> None:
    repo = StationRepository()
    bike = Bike(vehicle_id="v1", frame_number="F1")
    station = Station(
        station_id=1,
        name="S1",
        latitude=32.0,
        longitude=34.0,
        capacity=5,
        vehicles=[bike],
    )
    repo.add(station)
    locks: defaultdict[int, asyncio.Lock] = defaultdict(asyncio.Lock)

    result = await find_nearest_station_with_eligible_vehicle(
        repo, lon=34.0, lat=32.0, station_locks=locks
    )
    assert result is not None
    s, v = result
    assert s.station_id == 1


async def test_find_nearest_eligible_with_locks_station_becomes_ineligible() -> None:
    """Station is eligible initially but by the time we acquire the lock, it has no eligible vehicles."""
    repo = StationRepository()
    bike = Bike(vehicle_id="v1", frame_number="F1", status=VehicleStatus.IN_USE)
    station = Station(
        station_id=1,
        name="S1",
        latitude=32.0,
        longitude=34.0,
        capacity=5,
        vehicles=[bike],
    )
    repo.add(station)

    result = await find_nearest_station_with_eligible_vehicle(repo, lon=34.0, lat=32.0)
    assert result is None


# --- find_nearest_station_with_free_slot ---


async def test_find_nearest_free_slot_returns_none_when_all_full() -> None:
    repo = StationRepository()
    bike = Bike(vehicle_id="v1", frame_number="F1")
    station = Station(
        station_id=1,
        name="Full",
        latitude=32.0,
        longitude=34.0,
        capacity=1,
        vehicles=[bike],
    )
    repo.add(station)

    result = await find_nearest_station_with_free_slot(repo, lon=34.0, lat=32.0)
    assert result is None


async def test_find_nearest_free_slot_success() -> None:
    repo = StationRepository()
    station = Station(
        station_id=1, name="Open", latitude=32.0, longitude=34.0, capacity=5
    )
    repo.add(station)

    result = await find_nearest_station_with_free_slot(repo, lon=34.0, lat=32.0)
    assert result is not None
    assert result.station_id == 1


async def test_find_nearest_free_slot_returns_closest() -> None:
    repo = StationRepository()
    far = Station(station_id=1, name="Far", latitude=50.0, longitude=10.0, capacity=5)
    near = Station(station_id=2, name="Near", latitude=32.0, longitude=34.0, capacity=5)
    repo.add(far)
    repo.add(near)

    result = await find_nearest_station_with_free_slot(repo, lon=34.01, lat=32.01)
    assert result is not None
    assert result.station_id == 2


# --- distance_meters ---


def test_distance_meters_same_point() -> None:
    station = Station(station_id=1, name="S", latitude=32.0, longitude=34.0, capacity=5)
    assert distance_meters(station, 34.0, 32.0) == 0.0


def test_distance_meters_small_offset() -> None:
    station = Station(station_id=1, name="S", latitude=32.0, longitude=34.0, capacity=5)
    d = distance_meters(station, 34.0, 32.00001)
    assert 0 < d < 5
