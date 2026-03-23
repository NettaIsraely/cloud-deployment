"""Integration tests for the POST /vehicle/treat endpoint."""

from datetime import date

from fastapi.testclient import TestClient

from tlvflow.api.app import app
from tlvflow.domain.enums import TreatmentType, VehicleStatus
from tlvflow.domain.stations import Station
from tlvflow.domain.vehicles import Bike, Scooter
from tlvflow.persistence.degraded_vehicles_repository import DegradedVehiclesRepository
from tlvflow.persistence.in_memory import StationRepository, VehicleRepository
from tlvflow.persistence.maintenance_repository import MaintenanceRepository


def test_treat_degrades_vehicle_resets_and_relocates() -> None:
    vehicle_repo = VehicleRepository()
    station_repo = StationRepository()
    maintenance_repo = MaintenanceRepository()
    degraded_repo = DegradedVehiclesRepository()

    v1 = Bike(vehicle_id="v1", frame_number="F1", status=VehicleStatus.DEGRADED)
    vehicle_repo.add(v1)
    degraded_repo.add(v1)

    station_a = Station(
        station_id=1, name="A", latitude=32.0, longitude=34.0, capacity=5
    )
    station_a.dock(v1)
    station_repo.add(station_a)

    station_b = Station(
        station_id=2, name="B", latitude=32.1, longitude=34.1, capacity=5
    )
    station_repo.add(station_b)

    with TestClient(app) as client:
        client.app.state.vehicle_repository = vehicle_repo
        client.app.state.station_repository = station_repo
        client.app.state.maintenance_repository = maintenance_repo
        client.app.state.degraded_vehicles_repository = degraded_repo

        resp = client.post("/vehicle/treat")

    assert resp.status_code == 200
    data = resp.json()
    assert "v1" in data
    assert v1.check_status() == VehicleStatus.AVAILABLE
    assert v1.rides_since_last_treated == 0
    assert v1.last_treated_date == date.today()
    assert v1 not in station_a.vehicles
    assert v1 in station_b.vehicles
    assert len(maintenance_repo.get_all()) == 1
    assert degraded_repo.get_by_id("v1") is None
    event = maintenance_repo.get_all()[0]
    assert event._treatments == [
        TreatmentType.CHAIN_LUBRICATION,
        TreatmentType.GENERAL_INSPECTION,
    ]


def test_treat_high_ride_vehicle_resets_stays_at_station() -> None:
    vehicle_repo = VehicleRepository()
    station_repo = StationRepository()
    maintenance_repo = MaintenanceRepository()
    degraded_repo = DegradedVehiclesRepository()

    v2 = Bike(vehicle_id="v2", frame_number="F2", status=VehicleStatus.AVAILABLE)
    v2.rides_since_last_treated = 7
    vehicle_repo.add(v2)

    station_a = Station(
        station_id=1, name="A", latitude=32.0, longitude=34.0, capacity=5
    )
    station_a.dock(v2)
    station_repo.add(station_a)

    with TestClient(app) as client:
        client.app.state.vehicle_repository = vehicle_repo
        client.app.state.station_repository = station_repo
        client.app.state.maintenance_repository = maintenance_repo
        client.app.state.degraded_vehicles_repository = degraded_repo

        resp = client.post("/vehicle/treat")

    assert resp.status_code == 200
    data = resp.json()
    assert "v2" in data
    assert v2.check_status() == VehicleStatus.AVAILABLE
    assert v2.rides_since_last_treated == 0
    assert v2.last_treated_date == date.today()
    assert v2 in station_a.vehicles
    assert len(maintenance_repo.get_all()) == 1
    event = maintenance_repo.get_all()[0]
    assert event._treatments == [
        TreatmentType.CHAIN_LUBRICATION,
        TreatmentType.GENERAL_INSPECTION,
    ]


def test_treat_scooter_applies_scooter_treatments() -> None:
    vehicle_repo = VehicleRepository()
    station_repo = StationRepository()
    maintenance_repo = MaintenanceRepository()
    degraded_repo = DegradedVehiclesRepository()

    s1 = Scooter(vehicle_id="s1", frame_number="FS1", status=VehicleStatus.AVAILABLE)
    s1.rides_since_last_treated = 7
    vehicle_repo.add(s1)

    station_a = Station(
        station_id=1, name="A", latitude=32.0, longitude=34.0, capacity=5
    )
    station_a.dock(s1)
    station_repo.add(station_a)

    with TestClient(app) as client:
        client.app.state.vehicle_repository = vehicle_repo
        client.app.state.station_repository = station_repo
        client.app.state.maintenance_repository = maintenance_repo
        client.app.state.degraded_vehicles_repository = degraded_repo

        resp = client.post("/vehicle/treat")

    assert resp.status_code == 200
    data = resp.json()
    assert "s1" in data
    assert s1.check_status() == VehicleStatus.AVAILABLE
    assert s1.rides_since_last_treated == 0
    assert len(maintenance_repo.get_all()) == 1
    event = maintenance_repo.get_all()[0]
    assert event._treatments == [
        TreatmentType.BATTERY_INSPECTION,
        TreatmentType.SCOOTER_FIRMWARE_UPDATE,
    ]


def test_treat_ignores_ineligible_vehicles() -> None:
    vehicle_repo = VehicleRepository()
    station_repo = StationRepository()
    maintenance_repo = MaintenanceRepository()
    degraded_repo = DegradedVehiclesRepository()

    v3 = Bike(vehicle_id="v3", frame_number="F3", status=VehicleStatus.AVAILABLE)
    v3.rides_since_last_treated = 2
    vehicle_repo.add(v3)

    station_a = Station(
        station_id=1, name="A", latitude=32.0, longitude=34.0, capacity=5
    )
    station_repo.add(station_a)

    with TestClient(app) as client:
        client.app.state.vehicle_repository = vehicle_repo
        client.app.state.station_repository = station_repo
        client.app.state.maintenance_repository = maintenance_repo
        client.app.state.degraded_vehicles_repository = degraded_repo

        resp = client.post("/vehicle/treat")

    assert resp.status_code == 200
    assert resp.json() == []
    assert v3.check_status() == VehicleStatus.AVAILABLE
    assert v3.rides_since_last_treated == 2
    assert len(maintenance_repo.get_all()) == 0
