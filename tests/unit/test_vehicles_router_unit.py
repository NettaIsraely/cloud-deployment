"""Unit tests for vehicles_router: treat edge cases and report-degraded endpoint."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from tlvflow.api.app import app
from tlvflow.domain.enums import VehicleStatus
from tlvflow.domain.rides import Ride
from tlvflow.domain.vehicles import Bike
from tlvflow.persistence.active_users_repository import ActiveUsersRepository
from tlvflow.persistence.degraded_vehicles_repository import DegradedVehiclesRepository
from tlvflow.persistence.in_memory import StationRepository, VehicleRepository
from tlvflow.persistence.maintenance_repository import MaintenanceRepository
from tlvflow.persistence.rides_repository import RidesRepository
from tlvflow.persistence.users_repository import UsersRepository


def _setup_full_state(client: TestClient) -> None:
    client.app.state.vehicle_repository = VehicleRepository()
    client.app.state.station_repository = StationRepository()
    client.app.state.maintenance_repository = MaintenanceRepository()
    client.app.state.degraded_vehicles_repository = DegradedVehiclesRepository()
    client.app.state.rides_repository = RidesRepository()
    client.app.state.active_users_repository = ActiveUsersRepository()
    client.app.state.users_repository = UsersRepository()
    client.app.state.treat_vehicles_lock = asyncio.Lock()
    client.app.state.station_locks = __import__("collections").defaultdict(asyncio.Lock)
    client.app.state.user_rides_locks = __import__("collections").defaultdict(
        asyncio.Lock
    )


# --- /vehicle/treat: repo not initialized ---


def test_treat_vehicle_repo_missing_500() -> None:
    with TestClient(app) as client:
        _setup_full_state(client)
        client.app.state.vehicle_repository = None
        resp = client.post("/vehicle/treat")
    assert resp.status_code == 500


def test_treat_station_repo_missing_500() -> None:
    with TestClient(app) as client:
        _setup_full_state(client)
        client.app.state.station_repository = None
        resp = client.post("/vehicle/treat")
    assert resp.status_code == 500


def test_treat_maintenance_repo_missing_500() -> None:
    with TestClient(app) as client:
        _setup_full_state(client)
        client.app.state.maintenance_repository = None
        resp = client.post("/vehicle/treat")
    assert resp.status_code == 500


def test_treat_degraded_repo_missing_500() -> None:
    with TestClient(app) as client:
        _setup_full_state(client)
        client.app.state.degraded_vehicles_repository = None
        resp = client.post("/vehicle/treat")
    assert resp.status_code == 500


def test_treat_lock_missing_500() -> None:
    with TestClient(app) as client:
        _setup_full_state(client)
        client.app.state.treat_vehicles_lock = None
        resp = client.post("/vehicle/treat")
    assert resp.status_code == 500


# --- /vehicle/report-degraded ---


def test_report_degraded_repos_missing_raises() -> None:
    """If rides_repo is None, RuntimeError is raised (500)."""
    with TestClient(app, raise_server_exceptions=False) as client:
        _setup_full_state(client)
        client.app.state.rides_repository = None
        resp = client.post(
            "/vehicle/report-degraded", json={"user_id": "u1", "vehicle_id": "v1"}
        )
    assert resp.status_code == 500


def test_report_degraded_vehicle_repo_missing_raises() -> None:
    with TestClient(app, raise_server_exceptions=False) as client:
        _setup_full_state(client)
        client.app.state.vehicle_repository = None
        resp = client.post(
            "/vehicle/report-degraded", json={"user_id": "u1", "vehicle_id": "v1"}
        )
    assert resp.status_code == 500


def test_report_degraded_degraded_repo_missing_raises() -> None:
    with TestClient(app, raise_server_exceptions=False) as client:
        _setup_full_state(client)
        client.app.state.degraded_vehicles_repository = None
        resp = client.post(
            "/vehicle/report-degraded", json={"user_id": "u1", "vehicle_id": "v1"}
        )
    assert resp.status_code == 500


def test_report_degraded_active_repo_missing_raises() -> None:
    with TestClient(app, raise_server_exceptions=False) as client:
        _setup_full_state(client)
        client.app.state.active_users_repository = None
        resp = client.post(
            "/vehicle/report-degraded", json={"user_id": "u1", "vehicle_id": "v1"}
        )
    assert resp.status_code == 500


def test_report_degraded_locks_missing_raises() -> None:
    with TestClient(app, raise_server_exceptions=False) as client:
        _setup_full_state(client)
        client.app.state.user_rides_locks = None
        resp = client.post(
            "/vehicle/report-degraded", json={"user_id": "u1", "vehicle_id": "v1"}
        )
    assert resp.status_code == 500


def test_report_degraded_success_during_active_ride() -> None:
    with TestClient(app) as client:
        _setup_full_state(client)
        bike = Bike(vehicle_id="v1", frame_number="F1", status=VehicleStatus.AVAILABLE)
        client.app.state.vehicle_repository.add(bike)

        ride = Ride(user_id="u1", vehicle_id="v1", start_time=datetime.now(UTC))
        client.app.state.rides_repository.add(ride)
        client.app.state.active_users_repository.set_active("u1", ride.ride_id)

        resp = client.post(
            "/vehicle/report-degraded", json={"user_id": "u1", "vehicle_id": "v1"}
        )
    assert resp.status_code == 200
    assert resp.json()["result"] == "ok"


def test_report_degraded_vehicle_not_found_404() -> None:
    with TestClient(app) as client:
        _setup_full_state(client)
        ride = Ride(user_id="u1", vehicle_id="v_missing", start_time=datetime.now(UTC))
        client.app.state.rides_repository.add(ride)
        client.app.state.active_users_repository.set_active("u1", ride.ride_id)

        resp = client.post(
            "/vehicle/report-degraded",
            json={"user_id": "u1", "vehicle_id": "v_missing"},
        )
    assert resp.status_code == 404


def test_report_degraded_no_active_ride_409() -> None:
    with TestClient(app) as client:
        _setup_full_state(client)
        resp = client.post(
            "/vehicle/report-degraded", json={"user_id": "u1", "vehicle_id": "v1"}
        )
    assert resp.status_code == 409
