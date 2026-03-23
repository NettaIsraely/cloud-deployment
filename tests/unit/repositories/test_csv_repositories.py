from pathlib import Path

from tlvflow.domain.enums import VehicleStatus
from tlvflow.domain.vehicles import Bike, EBike, Scooter
from tlvflow.persistence.in_memory import StationRepository, VehicleRepository


def test_vehicle_repository_loads_csv(tmp_path: Path) -> None:
    csv_path = tmp_path / "vehicles.csv"
    csv_path.write_text(
        "vehicle_id,station_id,vehicle_type,status,rides_since_last_treated,last_treated_date,"
        "frame_number,has_child_seat,battery_health\n"
        "v1,1,bicycle,available,0,2026-01-01,f1,true,\n"
        "v2,2,electric_bicycle,in_use,3,2026-01-02,f2,,88\n"
        "v3,3,scooter,degraded,7,2026-01-03,f3,,50\n",
        encoding="utf-8",
    )

    repo = VehicleRepository()
    count = repo.load_from_csv(csv_path)

    assert count == 3
    assert len(repo.get_all()) == 3

    v2 = repo.get_by_id("v2")
    assert v2 is not None
    assert v2._vehicle_id == "v2"
    assert v2._frame_number == "f2"
    assert v2._Vehicle__status == VehicleStatus.IN_USE

    v3 = repo.get_by_id("v3")
    assert v3 is not None
    assert v3._Vehicle__status == VehicleStatus.DEGRADED


def test_vehicle_repository_add_get_clear() -> None:
    repo = VehicleRepository()

    assert repo.get_by_id("missing") is None

    bike = Bike(vehicle_id="b1", frame_number="fb1", has_child_seat=False)
    ebike = EBike(vehicle_id="e1", frame_number="fe1", battery_health=90)
    scooter = Scooter(vehicle_id="s1", frame_number="fs1", battery_health=40)

    repo.add(bike)
    repo.add(ebike)
    repo.add(scooter)

    assert repo.get_by_id("b1") is bike
    assert repo.get_by_id("e1") is ebike
    assert repo.get_by_id("s1") is scooter
    assert len(repo.get_all()) == 3

    repo.clear()
    assert repo.get_all() == []


def test_vehicle_repository_load_missing_file_returns_zero(tmp_path: Path) -> None:
    repo = VehicleRepository()
    count = repo.load_from_csv(tmp_path / "does_not_exist.csv")
    assert count == 0
    assert repo.get_all() == []


def test_station_repository_loads_csv(tmp_path: Path) -> None:
    csv_path = tmp_path / "stations.csv"
    csv_path.write_text(
        "station_id,name,lat,lon,max_capacity\n"
        "1,Dizengoff,32.0853,34.7818,10\n"
        "2,Habima,32.0736,34.7784,15\n",
        encoding="utf-8",
    )

    repo = StationRepository()
    count = repo.load_from_csv(csv_path)

    assert count == 2
    assert len(repo.get_all()) == 2

    s1 = repo.get_by_id(1)
    assert s1 is not None
    assert s1.station_id == 1
    assert s1.name == "Dizengoff"
    assert s1.capacity == 10


def test_station_repository_add_get_clear() -> None:
    from tlvflow.domain.stations import Station

    repo = StationRepository()
    assert repo.get_by_id(999) is None

    s = Station(
        station_id=3,
        name="Azrieli",
        latitude=32.0740,
        longitude=34.7922,
        capacity=7,
    )

    repo.add(s)
    assert repo.get_by_id(3) is s
    assert len(repo.get_all()) == 1

    repo.clear()
    assert repo.get_all() == []


def test_station_repository_load_missing_file_returns_zero(tmp_path: Path) -> None:
    repo = StationRepository()
    count = repo.load_from_csv(tmp_path / "does_not_exist.csv")
    assert count == 0
    assert repo.get_all() == []
