"""
Integration tests for the stations endpoints."""

from fastapi.testclient import TestClient

from tlvflow.api.app import app
from tlvflow.domain.stations import Station
from tlvflow.persistence.in_memory import StationRepository


def test_nearest_station_integration_returns_closest() -> None:
    with TestClient(app) as client:
        repo = StationRepository()
        repo.add(
            Station(
                station_id=1,
                name="Close",
                latitude=32.0,
                longitude=34.0,
                capacity=5,
            )
        )
        repo.add(
            Station(
                station_id=2,
                name="Far",
                latitude=50.0,
                longitude=10.0,
                capacity=5,
            )
        )

        # Override whatever lifespan loaded from the real CSV files.
        client.app.state.station_repository = repo

        resp = client.get("/stations/nearest", params={"lon": 34.01, "lat": 32.01})

    assert resp.status_code == 200
    data = resp.json()
    assert data["station_id"] == 1
    assert data["name"] == "Close"


def test_nearest_station_integration_returns_404_when_no_stations() -> None:
    with TestClient(app) as client:
        client.app.state.station_repository = StationRepository()

        resp = client.get("/stations/nearest", params={"lon": 34.0, "lat": 32.0})

    assert resp.status_code == 404
    assert resp.json()["detail"] == "No stations available"
