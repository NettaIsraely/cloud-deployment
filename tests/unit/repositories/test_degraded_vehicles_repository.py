"""Unit tests for DegradedVehiclesRepository (dumb store; no station logic)."""

from __future__ import annotations

from tlvflow.domain.enums import VehicleStatus
from tlvflow.domain.vehicles import Bike
from tlvflow.persistence.degraded_vehicles_repository import (
    DegradedVehiclesRepository,
)
from tlvflow.persistence.in_memory import VehicleRepository


def test_add_and_get() -> None:
    repo = DegradedVehiclesRepository()
    bike = Bike("v1", "F1", status=VehicleStatus.DEGRADED)
    repo.add(bike)
    assert repo.get_all() == [bike]
    assert repo.get_by_id("v1") is bike
    assert repo.get_by_id("  v1  ") is bike


def test_remove_returns_vehicle() -> None:
    repo = DegradedVehiclesRepository()
    bike = Bike("v1", "F1", status=VehicleStatus.DEGRADED)
    repo.add(bike)
    out = repo.remove("v1")
    assert out is bike
    assert repo.get_by_id("v1") is None
    assert repo.get_all() == []


def test_remove_invalid_id_returns_none() -> None:
    repo = DegradedVehiclesRepository()
    bike = Bike("v1", "F1", status=VehicleStatus.DEGRADED)
    repo.add(bike)
    assert repo.remove("") is None
    assert repo.remove("  ") is None
    assert repo.remove("v99") is None
    assert repo.get_all() == [bike]


def test_clear() -> None:
    repo = DegradedVehiclesRepository()
    bike = Bike("v1", "F1", status=VehicleStatus.DEGRADED)
    repo.add(bike)
    repo.clear()
    assert repo.get_all() == []
    assert repo.get_by_id("v1") is None


def test_snapshot_and_restore_round_trip() -> None:
    vehicle_repo = VehicleRepository()
    bike = Bike("v1", "F1", status=VehicleStatus.DEGRADED)
    vehicle_repo.add(bike)

    repo = DegradedVehiclesRepository()
    repo.add(bike)
    snapshot = repo.snapshot()
    assert snapshot == {"vehicle_ids": ["v1"]}

    repo.clear()
    assert repo.get_all() == []
    repo.restore(snapshot, vehicle_repo=vehicle_repo)
    assert len(repo.get_all()) == 1
    assert repo.get_by_id("v1") is bike
