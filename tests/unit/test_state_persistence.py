from datetime import date
from pathlib import Path

import pytest

from tlvflow.domain.enums import VehicleStatus
from tlvflow.domain.stations import Station
from tlvflow.domain.vehicles import Bike, EBike, Vehicle
from tlvflow.persistence.in_memory import (
    StationRepository,
    VehicleRepository,
    _vehicle_from_dict,
    _vehicle_to_dict,
)
from tlvflow.persistence.state_store import StateStore


def test_state_store_round_trip_persists_vehicle_fields(tmp_path: Path) -> None:
    store = StateStore(path=tmp_path / "state.json")

    vehicle_repo = VehicleRepository()
    station_repo = StationRepository()

    bike = Bike(
        vehicle_id="v1",
        frame_number="F-1",
        has_child_seat=True,
        status=VehicleStatus.IN_USE,
    )
    bike.rides_since_last_treated = 9
    bike.has_helmet = True
    bike._last_treated_date = date(2026, 3, 1)

    ebike = EBike(
        vehicle_id="v2",
        frame_number="F-2",
        battery_health=15,
        status=VehicleStatus.AWAITING_REPORT_REVIEW,
    )

    vehicle_repo.add(bike)
    vehicle_repo.add(ebike)

    store.save(
        {
            "vehicles": vehicle_repo.snapshot(),
            "stations": station_repo.snapshot(),
        }
    )

    reloaded_vehicle_repo = VehicleRepository()
    reloaded_station_repo = StationRepository()

    snapshot = store.load()
    reloaded_vehicle_repo.restore(snapshot["vehicles"])
    reloaded_station_repo.restore(
        snapshot["stations"], vehicle_repo=reloaded_vehicle_repo
    )

    v1 = reloaded_vehicle_repo.get_by_id("v1")
    assert v1 is not None
    assert v1.check_status() == VehicleStatus.IN_USE
    assert v1.rides_since_last_treated == 9
    assert v1.has_helmet is True
    assert v1.last_treated_date == date(2026, 3, 1)

    v2 = reloaded_vehicle_repo.get_by_id("v2")
    assert v2 is not None
    assert v2.check_status() == VehicleStatus.AWAITING_REPORT_REVIEW


def test_station_snapshot_round_trip_preserves_docked_vehicle_ids(
    tmp_path: Path,
) -> None:
    store = StateStore(path=tmp_path / "state.json")

    vehicle_repo = VehicleRepository()
    station_repo = StationRepository()

    bike = Bike(vehicle_id="v10", frame_number="F-10", status=VehicleStatus.AVAILABLE)
    vehicle_repo.add(bike)

    station = Station(
        station_id=1,
        name="Dizengoff",
        latitude=32.0853,
        longitude=34.7818,
        capacity=2,
    )
    station.dock(bike)
    station_repo.add(station)

    store.save(
        {
            "vehicles": vehicle_repo.snapshot(),
            "stations": station_repo.snapshot(),
        }
    )

    reloaded_vehicle_repo = VehicleRepository()
    reloaded_station_repo = StationRepository()
    snapshot = store.load()

    reloaded_vehicle_repo.restore(snapshot["vehicles"])
    reloaded_station_repo.restore(
        snapshot["stations"], vehicle_repo=reloaded_vehicle_repo
    )
    # Station restore already docks vehicles from snapshot; do not call link_vehicles (would double-dock).

    restored_station = reloaded_station_repo.get_by_id(1)
    assert restored_station is not None
    assert [v._vehicle_id for v in restored_station.vehicles] == ["v10"]


class DummyVehicle(Vehicle):
    @property
    def is_electric(self) -> bool:
        return False


def test_vehicle_to_dict_rejects_unsupported_vehicle_subclass() -> None:
    vehicle = DummyVehicle(
        vehicle_id="dv1",
        frame_number="F-DV1",
        status=VehicleStatus.AVAILABLE,
    )

    with pytest.raises(TypeError, match="Unsupported vehicle type"):
        _vehicle_to_dict(vehicle)


def test_vehicle_from_dict_rejects_invalid_vehicle_type() -> None:
    bad = {
        "vehicle_type": "spaceship",
        "vehicle_id": "v1",
        "frame_number": "F-1",
        "status": VehicleStatus.AVAILABLE.value,
    }

    with pytest.raises(ValueError, match="Invalid vehicle_type"):
        _vehicle_from_dict(bad)


def test_state_store_load_rejects_non_object_json(tmp_path) -> None:
    path = tmp_path / "state.json"
    path.write_text('["not", "an", "object"]', encoding="utf-8")

    store = StateStore(path=path)

    with pytest.raises(ValueError, match="expected a JSON object"):
        store.load()
