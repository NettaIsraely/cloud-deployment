"""Unit tests for rides_router: covers all uncovered branches."""

from __future__ import annotations

import asyncio
from uuid import uuid4

from fastapi.testclient import TestClient

from tlvflow.api.app import app
from tlvflow.domain.enums import VehicleStatus
from tlvflow.domain.payment_service import PaymentService
from tlvflow.domain.stations import Station
from tlvflow.domain.vehicles import Bike, EBike
from tlvflow.persistence.active_users_repository import ActiveUsersRepository
from tlvflow.persistence.degraded_vehicles_repository import DegradedVehiclesRepository
from tlvflow.persistence.in_memory import StationRepository, VehicleRepository
from tlvflow.persistence.maintenance_repository import MaintenanceRepository
from tlvflow.persistence.rides_repository import RidesRepository
from tlvflow.persistence.users_repository import UsersRepository


def _setup_full_state(client: TestClient) -> None:
    """Set up all required app state for ride endpoints."""
    client.app.state.users_repository = UsersRepository()
    client.app.state.rides_repository = RidesRepository()
    client.app.state.active_users_repository = ActiveUsersRepository()
    client.app.state.station_repository = StationRepository()
    client.app.state.vehicle_repository = VehicleRepository()
    client.app.state.maintenance_repository = MaintenanceRepository()
    client.app.state.degraded_vehicles_repository = DegradedVehiclesRepository()
    client.app.state.payment_service = PaymentService()
    client.app.state.station_locks = __import__("collections").defaultdict(asyncio.Lock)
    client.app.state.user_rides_locks = __import__("collections").defaultdict(
        asyncio.Lock
    )
    client.app.state.treat_vehicles_lock = asyncio.Lock()


def _register_user(client: TestClient, email: str | None = None) -> str:
    email = email or f"u-{uuid4().hex[:8]}@test.com"
    resp = client.post(
        "/register",
        json={
            "name": "Test User",
            "email": email,
            "password": "password123",
            "payment_method_id": "pm_1",
        },
    )
    assert resp.status_code == 201
    return resp.json()["user_id"]


def _add_bike_at_station(
    client: TestClient, vid: str, station_id: int
) -> tuple[Bike, Station]:
    bike = Bike(vehicle_id=vid, frame_number=f"F-{vid}", status=VehicleStatus.AVAILABLE)
    station = Station(
        station_id=station_id,
        name=f"St_{station_id}",
        latitude=32.0,
        longitude=34.0,
        capacity=10,
        vehicles=[bike],
    )
    client.app.state.vehicle_repository.add(bike)
    client.app.state.station_repository.add(station)
    return bike, station


# --- /ride/start: repo not initialized ---


def test_start_rides_repo_missing_returns_500() -> None:
    with TestClient(app) as client:
        _setup_full_state(client)
        client.app.state.rides_repository = None
        resp = client.post(
            "/ride/start", json={"user_id": "u1", "lon": 34.0, "lat": 32.0}
        )
    assert resp.status_code == 500


def test_start_active_users_repo_missing_returns_500() -> None:
    with TestClient(app) as client:
        _setup_full_state(client)
        client.app.state.active_users_repository = None
        resp = client.post(
            "/ride/start", json={"user_id": "u1", "lon": 34.0, "lat": 32.0}
        )
    assert resp.status_code == 500


def test_start_station_repo_missing_returns_500() -> None:
    with TestClient(app) as client:
        _setup_full_state(client)
        client.app.state.station_repository = None
        resp = client.post(
            "/ride/start", json={"user_id": "u1", "lon": 34.0, "lat": 32.0}
        )
    assert resp.status_code == 500


def test_start_users_repo_missing_returns_500() -> None:
    with TestClient(app) as client:
        _setup_full_state(client)
        client.app.state.users_repository = None
        resp = client.post(
            "/ride/start", json={"user_id": "u1", "lon": 34.0, "lat": 32.0}
        )
    assert resp.status_code == 500


def test_start_locks_missing_returns_500() -> None:
    with TestClient(app) as client:
        _setup_full_state(client)
        client.app.state.station_locks = None
        resp = client.post(
            "/ride/start", json={"user_id": "u1", "lon": 34.0, "lat": 32.0}
        )
    assert resp.status_code == 500


def test_start_no_eligible_station_returns_404() -> None:
    """start endpoint: no station with eligible vehicle → 404."""
    with TestClient(app) as client:
        _setup_full_state(client)
        user_id = _register_user(client)
        station = Station(
            station_id=1, name="S1", latitude=32.0, longitude=34.0, capacity=5
        )
        client.app.state.station_repository.add(station)
        resp = client.post(
            "/ride/start", json={"user_id": user_id, "lon": 34.0, "lat": 32.0}
        )
    assert resp.status_code == 404


# --- /ride/start-by-station: repo not initialized & error paths ---


def test_start_by_station_rides_repo_missing_returns_500() -> None:
    with TestClient(app) as client:
        _setup_full_state(client)
        client.app.state.rides_repository = None
        resp = client.post(
            "/ride/start-by-station", json={"user_id": "u1", "station_id": 1}
        )
    assert resp.status_code == 500


def test_start_by_station_active_users_repo_missing_returns_500() -> None:
    with TestClient(app) as client:
        _setup_full_state(client)
        client.app.state.active_users_repository = None
        resp = client.post(
            "/ride/start-by-station", json={"user_id": "u1", "station_id": 1}
        )
    assert resp.status_code == 500


def test_start_by_station_station_repo_missing_returns_500() -> None:
    with TestClient(app) as client:
        _setup_full_state(client)
        client.app.state.station_repository = None
        resp = client.post(
            "/ride/start-by-station", json={"user_id": "u1", "station_id": 1}
        )
    assert resp.status_code == 500


def test_start_by_station_users_repo_missing_returns_500() -> None:
    with TestClient(app) as client:
        _setup_full_state(client)
        client.app.state.users_repository = None
        resp = client.post(
            "/ride/start-by-station", json={"user_id": "u1", "station_id": 1}
        )
    assert resp.status_code == 500


def test_start_by_station_locks_missing_returns_500() -> None:
    with TestClient(app) as client:
        _setup_full_state(client)
        client.app.state.station_locks = None
        resp = client.post(
            "/ride/start-by-station", json={"user_id": "u1", "station_id": 1}
        )
    assert resp.status_code == 500


def test_start_by_station_user_not_found_404() -> None:
    with TestClient(app) as client:
        _setup_full_state(client)
        resp = client.post(
            "/ride/start-by-station", json={"user_id": "ghost", "station_id": 1}
        )
    assert resp.status_code == 404


def test_start_by_station_already_active_ride_409() -> None:
    with TestClient(app) as client:
        _setup_full_state(client)
        user_id = _register_user(client)
        _add_bike_at_station(client, "v1", 1)
        _add_bike_at_station(client, "v2", 2)

        resp1 = client.post(
            "/ride/start-by-station", json={"user_id": user_id, "station_id": 1}
        )
        assert resp1.status_code == 201

        resp2 = client.post(
            "/ride/start-by-station", json={"user_id": user_id, "station_id": 2}
        )
    assert resp2.status_code == 409


def test_start_by_station_station_not_found_404() -> None:
    with TestClient(app) as client:
        _setup_full_state(client)
        user_id = _register_user(client)
        resp = client.post(
            "/ride/start-by-station", json={"user_id": user_id, "station_id": 999}
        )
    assert resp.status_code == 404


def test_start_by_station_empty_station_returns_400() -> None:
    with TestClient(app) as client:
        _setup_full_state(client)
        user_id = _register_user(client)
        station = Station(
            station_id=3, name="Empty", latitude=32.0, longitude=34.0, capacity=5
        )
        client.app.state.station_repository.add(station)
        resp = client.post(
            "/ride/start-by-station", json={"user_id": user_id, "station_id": 3}
        )
    assert resp.status_code == 400


# --- /ride/start-by-vehicle ---


def test_start_by_vehicle_repos_not_init_returns_500() -> None:
    with TestClient(app) as client:
        _setup_full_state(client)
        client.app.state.vehicle_repository = None
        resp = client.post(
            "/ride/start-by-vehicle", json={"user_id": "u1", "vehicle_id": "v1"}
        )
    assert resp.status_code == 500


def test_start_by_vehicle_vehicle_not_found_returns_404() -> None:
    with TestClient(app) as client:
        _setup_full_state(client)
        user_id = _register_user(client)
        resp = client.post(
            "/ride/start-by-vehicle",
            json={"user_id": user_id, "vehicle_id": "nonexistent"},
        )
    assert resp.status_code == 404


def test_start_by_vehicle_not_at_station_returns_400() -> None:
    with TestClient(app) as client:
        _setup_full_state(client)
        user_id = _register_user(client)
        bike = Bike(vehicle_id="v_free", frame_number="FF1")
        client.app.state.vehicle_repository.add(bike)
        resp = client.post(
            "/ride/start-by-vehicle", json={"user_id": user_id, "vehicle_id": "v_free"}
        )
    assert resp.status_code == 400


def test_start_by_vehicle_locks_missing_returns_500() -> None:
    with TestClient(app) as client:
        _setup_full_state(client)
        user_id = _register_user(client)
        bike, station = _add_bike_at_station(client, "v_locked", 1)
        client.app.state.station_locks = None
        resp = client.post(
            "/ride/start-by-vehicle",
            json={"user_id": user_id, "vehicle_id": "v_locked"},
        )
    assert resp.status_code == 500


def test_start_by_vehicle_success() -> None:
    with TestClient(app) as client:
        _setup_full_state(client)
        user_id = _register_user(client)
        bike, station = _add_bike_at_station(client, "v_ok", 1)
        resp = client.post(
            "/ride/start-by-vehicle", json={"user_id": user_id, "vehicle_id": "v_ok"}
        )
    assert resp.status_code == 201
    data = resp.json()
    assert data["vehicle_id"] == "v_ok"
    assert data["start_station_id"] == 1
    assert data["vehicle_type"] == "bike"


def test_start_by_vehicle_permission_denied_returns_403() -> None:
    """Non-pro user trying to rent electric vehicle → 403."""
    with TestClient(app) as client:
        _setup_full_state(client)
        user_id = _register_user(client)
        ebike = EBike(vehicle_id="e1", frame_number="FE1")
        station = Station(
            station_id=1,
            name="S1",
            latitude=32.0,
            longitude=34.0,
            capacity=10,
            vehicles=[ebike],
        )
        client.app.state.vehicle_repository.add(ebike)
        client.app.state.station_repository.add(station)
        resp = client.post(
            "/ride/start-by-vehicle", json={"user_id": user_id, "vehicle_id": "e1"}
        )
    assert resp.status_code == 403


def test_start_by_vehicle_already_on_ride_returns_409() -> None:
    with TestClient(app) as client:
        _setup_full_state(client)
        user_id = _register_user(client)
        _add_bike_at_station(client, "v1", 1)
        bike2 = Bike(vehicle_id="v2", frame_number="F2")
        station2 = Station(
            station_id=2,
            name="S2",
            latitude=32.1,
            longitude=34.1,
            capacity=10,
            vehicles=[bike2],
        )
        client.app.state.vehicle_repository.add(bike2)
        client.app.state.station_repository.add(station2)

        resp1 = client.post(
            "/ride/start-by-vehicle", json={"user_id": user_id, "vehicle_id": "v1"}
        )
        assert resp1.status_code == 201

        resp2 = client.post(
            "/ride/start-by-vehicle", json={"user_id": user_id, "vehicle_id": "v2"}
        )
    assert resp2.status_code == 409


# --- /ride/rides/active ---


def test_get_active_ride_repos_missing_500() -> None:
    with TestClient(app) as client:
        _setup_full_state(client)
        client.app.state.active_users_repository = None
        resp = client.get("/ride/rides/active", params={"user_id": "u1"})
    assert resp.status_code == 500


def test_get_active_ride_rides_repo_missing_500() -> None:
    with TestClient(app) as client:
        _setup_full_state(client)
        client.app.state.rides_repository = None
        resp = client.get("/ride/rides/active", params={"user_id": "u1"})
    assert resp.status_code == 500


def test_get_active_ride_no_active_ride_404() -> None:
    with TestClient(app) as client:
        _setup_full_state(client)
        resp = client.get("/ride/rides/active", params={"user_id": "u1"})
    assert resp.status_code == 404


def test_get_active_ride_ride_not_found_404() -> None:
    """User has ride id mapped but ride object is missing from rides repo."""
    with TestClient(app) as client:
        _setup_full_state(client)
        client.app.state.active_users_repository.set_active("u1", "phantom-ride")
        resp = client.get("/ride/rides/active", params={"user_id": "u1"})
    assert resp.status_code == 404


def test_get_active_ride_success() -> None:
    with TestClient(app) as client:
        _setup_full_state(client)
        user_id = _register_user(client)
        _add_bike_at_station(client, "v1", 1)
        start = client.post(
            "/ride/start-by-station", json={"user_id": user_id, "station_id": 1}
        )
        assert start.status_code == 201
        ride_id = start.json()["ride_id"]

        resp = client.get("/ride/rides/active", params={"user_id": user_id})
    assert resp.status_code == 200
    data = resp.json()
    assert data["ride_id"] == ride_id
    assert "start_time" in data


# --- /ride/rides/history ---


def test_get_ride_history_repo_missing_500() -> None:
    with TestClient(app) as client:
        _setup_full_state(client)
        client.app.state.rides_repository = None
        resp = client.get("/ride/rides/history", params={"user_id": "u1"})
    assert resp.status_code == 500


def test_get_ride_history_empty() -> None:
    with TestClient(app) as client:
        _setup_full_state(client)
        resp = client.get("/ride/rides/history", params={"user_id": "u1"})
    assert resp.status_code == 200
    assert resp.json()["rides"] == []


def test_get_ride_history_returns_completed_rides() -> None:
    with TestClient(app) as client:
        _setup_full_state(client)
        user_id = _register_user(client)
        _add_bike_at_station(client, "v1", 1)
        start = client.post(
            "/ride/start-by-station", json={"user_id": user_id, "station_id": 1}
        )
        ride_id = start.json()["ride_id"]
        station = client.app.state.station_repository.get_by_id(1)
        end = client.post(
            "/ride/end",
            json={
                "ride_id": ride_id,
                "lon": station.longitude,
                "lat": station.latitude,
            },
        )
        assert end.status_code == 200

        resp = client.get("/ride/rides/history", params={"user_id": user_id})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["rides"]) == 1
    assert data["rides"][0]["ride_id"] == ride_id
    assert data["rides"][0]["fee"] == 15.0


# --- /ride/end: repo not initialized paths ---


def test_end_rides_repo_missing_500() -> None:
    with TestClient(app) as client:
        _setup_full_state(client)
        client.app.state.rides_repository = None
        resp = client.post(
            "/ride/end", json={"ride_id": "r1", "lon": 34.0, "lat": 32.0}
        )
    assert resp.status_code == 500


def test_end_active_users_repo_missing_500() -> None:
    with TestClient(app) as client:
        _setup_full_state(client)
        client.app.state.active_users_repository = None
        resp = client.post(
            "/ride/end", json={"ride_id": "r1", "lon": 34.0, "lat": 32.0}
        )
    assert resp.status_code == 500


def test_end_users_repo_missing_500() -> None:
    with TestClient(app) as client:
        _setup_full_state(client)
        client.app.state.users_repository = None
        resp = client.post(
            "/ride/end", json={"ride_id": "r1", "lon": 34.0, "lat": 32.0}
        )
    assert resp.status_code == 500


def test_end_vehicle_repo_missing_500() -> None:
    with TestClient(app) as client:
        _setup_full_state(client)
        client.app.state.vehicle_repository = None
        resp = client.post(
            "/ride/end", json={"ride_id": "r1", "lon": 34.0, "lat": 32.0}
        )
    assert resp.status_code == 500


def test_end_station_repo_missing_500() -> None:
    with TestClient(app) as client:
        _setup_full_state(client)
        client.app.state.station_repository = None
        resp = client.post(
            "/ride/end", json={"ride_id": "r1", "lon": 34.0, "lat": 32.0}
        )
    assert resp.status_code == 500


def test_end_payment_service_missing_500() -> None:
    with TestClient(app) as client:
        _setup_full_state(client)
        client.app.state.payment_service = None
        resp = client.post(
            "/ride/end", json={"ride_id": "r1", "lon": 34.0, "lat": 32.0}
        )
    assert resp.status_code == 500


def test_end_locks_missing_500() -> None:
    with TestClient(app) as client:
        _setup_full_state(client)
        client.app.state.station_locks = None
        resp = client.post(
            "/ride/end", json={"ride_id": "r1", "lon": 34.0, "lat": 32.0}
        )
    assert resp.status_code == 500


def test_end_ride_not_found_404() -> None:
    with TestClient(app) as client:
        _setup_full_state(client)
        resp = client.post(
            "/ride/end", json={"ride_id": "no-such-ride", "lon": 34.0, "lat": 32.0}
        )
    assert resp.status_code == 404


def test_end_ride_not_active_returns_404() -> None:
    """Ending a ride that is already ended → 404 ('is not active')."""
    with TestClient(app) as client:
        _setup_full_state(client)
        user_id = _register_user(client)
        _add_bike_at_station(client, "v1", 1)
        start = client.post(
            "/ride/start-by-station", json={"user_id": user_id, "station_id": 1}
        )
        ride_id = start.json()["ride_id"]
        station = client.app.state.station_repository.get_by_id(1)
        client.post(
            "/ride/end",
            json={
                "ride_id": ride_id,
                "lon": station.longitude,
                "lat": station.latitude,
            },
        )
        resp = client.post(
            "/ride/end",
            json={
                "ride_id": ride_id,
                "lon": station.longitude,
                "lat": station.latitude,
            },
        )
    assert resp.status_code == 404


def test_end_ride_far_from_station_returns_400() -> None:
    with TestClient(app) as client:
        _setup_full_state(client)
        user_id = _register_user(client)
        _add_bike_at_station(client, "v1", 1)
        start = client.post(
            "/ride/start-by-station", json={"user_id": user_id, "station_id": 1}
        )
        ride_id = start.json()["ride_id"]
        resp = client.post(
            "/ride/end", json={"ride_id": ride_id, "lon": 35.0, "lat": 33.0}
        )
    assert resp.status_code == 400 or resp.status_code == 404
