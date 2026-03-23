from tlvflow.domain.stations import Station
from tlvflow.persistence.in_memory import StationRepository
from tlvflow.services.stations_service import find_nearest_station, station_to_dict


async def test_find_nearest_station_returns_none_when_repo_empty() -> None:
    repo = StationRepository()

    result = await find_nearest_station(repo, lon=34.0, lat=32.0)

    assert result is None


async def test_find_nearest_station_returns_closest_station() -> None:
    repo = StationRepository()
    close_station = Station(
        station_id=1,
        name="Close",
        latitude=32.0,
        longitude=34.0,
        capacity=5,
    )
    far_station = Station(
        station_id=2,
        name="Far",
        latitude=50.0,
        longitude=10.0,
        capacity=5,
    )
    repo.add(far_station)
    repo.add(close_station)

    result = await find_nearest_station(repo, lon=34.01, lat=32.01)

    assert result is close_station


def test_station_to_dict_contains_expected_fields() -> None:
    station = Station(
        station_id=10,
        name="Test",
        latitude=32.1,
        longitude=34.8,
        capacity=3,
    )

    data = station_to_dict(station)

    assert data["station_id"] == 10
    assert data["name"] == "Test"
    assert data["lat"] == 32.1
    assert data["lon"] == 34.8
    assert data["max_capacity"] == 3
    assert "available_slots" in data
    assert "is_full" in data
    assert "is_empty" in data
