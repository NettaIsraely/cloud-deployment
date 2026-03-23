import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from tlvflow.api.routers.stations_router import router
from tlvflow.domain.stations import Station
from tlvflow.persistence.in_memory import StationRepository


@pytest.fixture()
def client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_nearest_station_returns_500_when_repo_missing(client: TestClient) -> None:
    resp = client.get("/stations/nearest", params={"lon": 34.0, "lat": 32.0})
    assert resp.status_code == 500
    assert resp.json()["detail"] == "Station repository not initialized"


def test_nearest_station_returns_404_when_no_stations(client: TestClient) -> None:
    client.app.state.station_repository = StationRepository()

    resp = client.get("/stations/nearest", params={"lon": 34.0, "lat": 32.0})
    assert resp.status_code == 404
    assert resp.json()["detail"] == "No stations available"


def test_nearest_station_returns_closest_station(client: TestClient) -> None:
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
    client.app.state.station_repository = repo

    resp = client.get("/stations/nearest", params={"lon": 34.01, "lat": 32.01})
    assert resp.status_code == 200

    data = resp.json()
    assert data["station_id"] == 1
    assert data["name"] == "Close"
    assert data["lat"] == 32.0
    assert data["lon"] == 34.0
    assert "available_slots" in data
    assert "is_full" in data
    assert "is_empty" in data


@pytest.mark.parametrize(
    "params",
    [
        {"lat": 32.0},  # missing lon
        {"lon": 34.0},  # missing lat
        {"lon": 200.0, "lat": 32.0},  # lon out of range
        {"lon": 34.0, "lat": 100.0},  # lat out of range
    ],
)
def test_nearest_station_validates_query_params(
    client: TestClient,
    params: dict[str, float],
) -> None:
    repo = StationRepository()
    repo.add(
        Station(
            station_id=1,
            name="Any",
            latitude=32.0,
            longitude=34.0,
            capacity=5,
        )
    )
    client.app.state.station_repository = repo

    resp = client.get("/stations/nearest", params=params)
    assert resp.status_code == 422
