import pytest

from tlvflow.domain.enums import VehicleStatus
from tlvflow.domain.stations import Station
from tlvflow.domain.vehicles import Bike


class DummyVehicle:
    pass


def make_station(*, capacity: int = 2, vehicles=None) -> Station:
    return Station(
        station_id=1,
        name="Dizengoff",
        latitude=32.0853,
        longitude=34.7818,
        capacity=capacity,
        vehicles=vehicles,
    )


def test_init_strips_name():
    station = Station(
        station_id=1,
        name="  Habima  ",
        latitude=0.0,
        longitude=0.0,
        capacity=1,
    )
    assert station.name == "Habima"


@pytest.mark.parametrize("station_id", [-1, 1.2, "1", None])
def test_init_rejects_invalid_station_id(station_id):
    with pytest.raises(ValueError, match="station_id must be a non-negative integer"):
        Station(
            station_id=station_id,  # type: ignore[arg-type]
            name="X",
            latitude=0.0,
            longitude=0.0,
            capacity=1,
        )


@pytest.mark.parametrize("name", ["", "   ", 123, None])
def test_init_rejects_invalid_name(name):
    with pytest.raises(ValueError, match="name must be a non-empty string"):
        Station(
            station_id=1,
            name=name,  # type: ignore[arg-type]
            latitude=0.0,
            longitude=0.0,
            capacity=1,
        )


@pytest.mark.parametrize("lat", [-90.1, 90.1, 1e9])
def test_init_rejects_latitude_out_of_range(lat):
    with pytest.raises(ValueError, match="latitude must be between -90 and 90"):
        Station(
            station_id=1,
            name="X",
            latitude=lat,
            longitude=0.0,
            capacity=1,
        )


@pytest.mark.parametrize("lon", [-180.1, 180.1, 1e9])
def test_init_rejects_longitude_out_of_range(lon):
    with pytest.raises(ValueError, match="longitude must be between -180 and 180"):
        Station(
            station_id=1,
            name="X",
            latitude=0.0,
            longitude=lon,
            capacity=1,
        )


@pytest.mark.parametrize("capacity", [0, -1, 1.5, "2", None])
def test_init_rejects_invalid_capacity(capacity):
    with pytest.raises(ValueError, match="capacity must be a positive integer"):
        Station(
            station_id=1,
            name="X",
            latitude=0.0,
            longitude=0.0,
            capacity=capacity,  # type: ignore[arg-type]
        )


def test_init_rejects_initial_vehicles_over_capacity():
    v1, v2, v3 = DummyVehicle(), DummyVehicle(), DummyVehicle()
    with pytest.raises(ValueError, match="initial vehicles cannot exceed capacity"):
        make_station(capacity=2, vehicles=[v1, v2, v3])


def test_properties_empty_station():
    station = make_station(capacity=3)
    assert station.available_slots == 3
    assert station.is_empty is True
    assert station.is_full is False
    assert station.vehicles == ()


def test_vehicles_property_returns_tuple_copy():
    v = DummyVehicle()
    station = make_station(capacity=2, vehicles=[v])

    vehicles_view = station.vehicles
    assert isinstance(vehicles_view, tuple)
    assert vehicles_view == (v,)

    station.dock(DummyVehicle())
    assert vehicles_view == (v,)


def test_dock_adds_vehicle_and_updates_slots():
    station = make_station(capacity=2)
    v = DummyVehicle()

    station.dock(v)

    assert station.vehicles == (v,)
    assert station.available_slots == 1
    assert station.is_empty is False
    assert station.is_full is False


def test_dock_when_full_raises():
    v1, v2 = DummyVehicle(), DummyVehicle()
    station = make_station(capacity=2, vehicles=[v1, v2])

    with pytest.raises(ValueError, match="station is full"):
        station.dock(DummyVehicle())


def test_undock_removes_vehicle():
    v = DummyVehicle()
    station = make_station(capacity=2, vehicles=[v])

    station.undock(v)

    assert station.vehicles == ()
    assert station.available_slots == 2
    assert station.is_empty is True


def test_undock_missing_vehicle_raises():
    station = make_station(capacity=2)
    with pytest.raises(ValueError, match="vehicle is not in this station"):
        station.undock(DummyVehicle())


def test_dock_and_undock_set_and_clear_vehicle_station_id():
    """Vehicle.station_id is set by dock and cleared by undock (O(1) lookup)."""
    bike = Bike("v1", "F1", status=VehicleStatus.AVAILABLE)
    assert bike.station_id is None

    station = Station(1, "Central", 32.0, 34.8, capacity=2)
    station.dock(bike)
    assert bike.station_id == 1

    station.undock(bike)
    assert bike.station_id is None


def test_simple_properties_are_exposed():
    station = Station(
        station_id=7,
        name="A",
        latitude=1.5,
        longitude=2.5,
        capacity=3,
    )

    assert station.station_id == 7
    assert station.name == "A"
    assert station.latitude == 1.5
    assert station.longitude == 2.5
    assert station.capacity == 3
