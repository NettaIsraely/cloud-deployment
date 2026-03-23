from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI

from tlvflow.api.app import lifespan
from tlvflow.domain.enums import VehicleStatus
from tlvflow.persistence.loaders import (
    _parse_bool,
    _parse_date,
    _parse_int,
    _parse_status,
    load_stations_from_csv,
    load_vehicles_from_csv,
)


def test_parse_helpers() -> None:
    assert _parse_bool("true") is True
    assert _parse_bool("YES") is True
    assert _parse_bool("0") is False

    assert _parse_int("", 7) == 7
    assert _parse_int(" 12 ", 0) == 12

    assert _parse_status("IN_USE") == VehicleStatus.IN_USE
    with pytest.raises(ValueError):
        _parse_status("maintenance")


def test_load_vehicles_missing_file(tmp_path: Path) -> None:
    assert load_vehicles_from_csv(tmp_path / "nope.csv") == []


def test_load_vehicles_empty_header(tmp_path: Path) -> None:
    path = tmp_path / "vehicles.csv"
    path.write_text("", encoding="utf-8")
    assert load_vehicles_from_csv(path) == []


def test_load_vehicles_branches_and_skips(tmp_path: Path) -> None:
    path = tmp_path / "vehicles.csv"
    path.write_text(
        "vehicle_id,station_id,vehicle_type,status,rides_since_last_treated,"
        "last_treated_date,frame_number,has_child_seat,battery_health\n"
        # Missing vehicle_id -> skip (covers missing id branch)
        ",1,bicycle,available,0,2026-01-01,f0,true,10\n"
        # Invalid type -> skip (covers invalid vehicle_type branch)
        "badtype,1,spaceship,available,0,2026-01-01,f1,false,10\n"
        # Bad status -> parse error -> skip (covers exception handler)
        "badstatus,1,bicycle,maintenance,0,2026-01-01,f2,false,10\n"
        # Bike with missing frame_number -> fallback FRAME-{id}
        "b1,1,bicycle,available,5,2026-01-01,,yes,\n"
        # EBike battery_health > 100 -> clamp to 100
        "e1,1,electric_bicycle,in_use,3,2026-01-01,f4,,999\n"
        # Scooter battery_health < 0 -> clamp to 0
        "s1,1,scooter,degraded,2,2026-01-01,f5,, -5\n",
        encoding="utf-8",
    )

    vehicles = load_vehicles_from_csv(path)
    assert [v._vehicle_id for v in vehicles] == ["b1", "e1", "s1"]

    bike, ebike, scooter = vehicles

    # frame fallback branch
    assert bike._frame_number == "FRAME-b1"

    # status parsing path (private attr in your Vehicle)
    assert ebike._Vehicle__status == VehicleStatus.IN_USE
    assert scooter._Vehicle__status == VehicleStatus.DEGRADED

    # clamp branches
    assert ebike.battery_health == 100
    assert scooter.battery_health == 0

    # ride_count assignment path
    assert bike.rides_since_last_treated == 5
    # last_treated_date from CSV (b1 row has 2026-01-01)
    assert bike.last_treated_date is not None
    assert bike.last_treated_date.year == 2026
    assert bike.last_treated_date.month == 1
    assert bike.last_treated_date.day == 1


def test_load_stations_missing_file(tmp_path: Path) -> None:
    assert load_stations_from_csv(tmp_path / "nope.csv") == []


def test_load_stations_empty_header(tmp_path: Path) -> None:
    path = tmp_path / "stations.csv"
    path.write_text("", encoding="utf-8")
    assert load_stations_from_csv(path) == []


def test_load_stations_branches_and_skips(tmp_path: Path) -> None:
    path = tmp_path / "stations.csv"
    path.write_text(
        "station_id,name,lat,lon,max_capacity\n"
        # Missing station_id -> skip
        ",Dizengoff,32.0,34.0,10\n"
        # Missing name -> skip
        "1,,32.0,34.0,10\n"
        # Missing lat -> skip
        "2,Habima,,34.0,10\n"
        # Missing lon -> skip
        "3,Azrieli,32.0,,10\n"
        # Missing capacity -> skip
        "4,Rothschild,32.0,34.0,\n"
        # Parse error -> skip (bad int/float)
        "x,Bug,notalat,34.0,10\n"
        # Valid row
        "5,Valid,32.0853,34.7818,7\n",
        encoding="utf-8",
    )

    stations = load_stations_from_csv(path)
    assert len(stations) == 1
    assert stations[0].station_id == 5
    assert stations[0].name == "Valid"
    assert stations[0].capacity == 7


def _make_csv(path: Path, header: list[str], rows: list[list[Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)


@pytest.mark.anyio
async def test_app_lifespan_executes_and_sets_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    Covers api/app.py lifespan block (lines 26-38) by:
    - creating temp CSVs
    - monkeypatching app module constants to point to them
    - running lifespan context manager
    """
    vehicles_csv = tmp_path / "vehicles.csv"
    stations_csv = tmp_path / "stations.csv"

    _make_csv(
        vehicles_csv,
        [
            "vehicle_id",
            "station_id",
            "vehicle_type",
            "status",
            "rides_since_last_treated",
            "last_treated_date",
            "frame_number",
            "has_child_seat",
            "battery_health",
        ],
        [
            ["v1", "1", "bicycle", "available", "0", "2026-01-01", "f1", "true", ""],
        ],
    )

    _make_csv(
        stations_csv,
        ["station_id", "name", "lat", "lon", "max_capacity"],
        [
            ["1", "Dizengoff", "32.0853", "34.7818", "10"],
        ],
    )

    import tlvflow.api.app as app_module

    state_json = tmp_path / "state.json"

    monkeypatch.setattr(app_module, "VEHICLES_CSV", vehicles_csv)
    monkeypatch.setattr(app_module, "STATIONS_CSV", stations_csv)
    monkeypatch.setattr(app_module, "STATE_JSON", state_json)

    app = FastAPI(lifespan=lifespan)

    async with lifespan(app):
        assert hasattr(app.state, "vehicle_repository")
        assert hasattr(app.state, "station_repository")

        v_repo = app.state.vehicle_repository
        s_repo = app.state.station_repository

        assert v_repo.get_by_id("v1") is not None
        assert s_repo.get_by_id(1) is not None


def test_parse_date_empty_returns_none() -> None:
    assert _parse_date("") is None
    assert _parse_date("   ") is None


def test_parse_date_invalid_returns_none() -> None:
    assert _parse_date("not-a-date") is None
    assert _parse_date("2026-99-99") is None
