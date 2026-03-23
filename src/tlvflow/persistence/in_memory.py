"""In-memory storage repositories with CSV loading."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from tlvflow.domain.enums import VehicleStatus
from tlvflow.domain.stations import Station
from tlvflow.domain.vehicles import Bike, EBike, Scooter, Vehicle
from tlvflow.persistence.loaders import load_stations_from_csv, load_vehicles_from_csv


class VehicleRepository:
    """In-memory repository for vehicles, optionally loaded from CSV."""

    def __init__(self) -> None:
        self._vehicles: dict[str, Vehicle] = {}

    def load_from_csv(self, path: str | Path) -> int:
        """
        Load vehicles from a CSV file into memory.

        Args:
            path: Path to the CSV file.

        Returns:
            Number of vehicles loaded.
        """
        vehicles = load_vehicles_from_csv(path)
        for vehicle in vehicles:
            self._vehicles[vehicle._vehicle_id] = vehicle
        return len(vehicles)

    def snapshot(self) -> dict[str, Any]:
        """Return a JSON-serializable snapshot of the repository."""
        return {
            vehicle_id: _vehicle_to_dict(vehicle)
            for vehicle_id, vehicle in self._vehicles.items()
        }

    def restore(self, snapshot: dict[str, Any]) -> None:
        """Replace the repository contents from a snapshot."""
        self._vehicles.clear()
        for vehicle_id, raw in snapshot.items():
            vehicle = _vehicle_from_dict(raw)
            self._vehicles[vehicle_id] = vehicle

    def get_all(self) -> list[Vehicle]:
        """Return all vehicles in memory."""
        return list(self._vehicles.values())

    def get_by_id(self, vehicle_id: str) -> Vehicle | None:
        """Return a vehicle by ID, or None if not found."""
        return self._vehicles.get(vehicle_id)

    def add(self, vehicle: Vehicle) -> None:
        """Add or replace a vehicle."""
        self._vehicles[vehicle._vehicle_id] = vehicle

    def clear(self) -> None:
        """Remove all vehicles from memory."""
        self._vehicles.clear()


class StationRepository:
    """In-memory repository for stations, optionally loaded from CSV."""

    def __init__(self) -> None:
        self._stations: dict[int, Station] = {}

    def load_from_csv(self, path: str | Path) -> int:
        """
        Load stations from a CSV file into memory.

        Args:
            path: Path to the CSV file.

        Returns:
            Number of stations loaded.
        """
        stations = load_stations_from_csv(path)
        for station in stations:
            self._stations[station.station_id] = station
        return len(stations)

    def snapshot(self) -> dict[str, Any]:
        """Return a JSON-serializable snapshot of the repository."""
        return {
            str(station_id): _station_to_dict(station)
            for station_id, station in self._stations.items()
        }

    def restore(
        self, snapshot: dict[str, Any], *, vehicle_repo: VehicleRepository
    ) -> None:
        """Replace the repository contents from a snapshot. Re-dock vehicles using each station's vehicle_ids so vehicles get station_id set."""
        self._stations.clear()

        for station_id_str, raw in snapshot.items():
            station, vehicle_ids = _station_from_dict(raw)
            station_id = int(station_id_str)
            self._stations[station_id] = station
            for vid in vehicle_ids:
                vehicle = vehicle_repo.get_by_id(vid)
                if vehicle is not None:
                    vehicle._station_id = station_id
                    station.dock(vehicle)

    def get_all(self) -> list[Station]:
        """Return all stations in memory."""
        return list(self._stations.values())

    def get_by_id(self, station_id: int) -> Station | None:
        """Return a station by ID, or None if not found."""
        return self._stations.get(station_id)

    def add(self, station: Station) -> None:
        """Add or replace a station."""
        self._stations[station.station_id] = station

    def clear(self) -> None:
        """Remove all stations from memory."""
        self._stations.clear()


def _vehicle_to_dict(vehicle: Vehicle) -> dict[str, Any]:
    data: dict[str, Any] = {
        "vehicle_id": vehicle._vehicle_id,
        "frame_number": vehicle._frame_number,
        "status": vehicle.check_status().value,
        "rides_since_last_treated": int(vehicle.rides_since_last_treated),
        "last_treated_date": (
            vehicle.last_treated_date.isoformat()
            if vehicle.last_treated_date is not None
            else None
        ),
        "has_helmet": bool(vehicle.has_helmet),
        "station_id": vehicle._station_id,
    }

    if isinstance(vehicle, Bike):
        data["vehicle_type"] = "bike"
        data["has_child_seat"] = bool(vehicle.has_child_seat)
    elif isinstance(vehicle, EBike):
        data["vehicle_type"] = "ebike"
        data["battery_health"] = int(vehicle.battery_health)
    elif isinstance(vehicle, Scooter):
        data["vehicle_type"] = "scooter"
        data["battery_health"] = int(vehicle.battery_health)
    else:
        raise TypeError(f"Unsupported vehicle type: {type(vehicle)!r}")

    return data


def _vehicle_from_dict(data: dict[str, Any]) -> Vehicle:
    vehicle_type = str(data["vehicle_type"])
    status = VehicleStatus(str(data.get("status", VehicleStatus.AVAILABLE.value)))

    vehicle_id = str(data["vehicle_id"])
    frame_number = str(data.get("frame_number", f"FRAME-{vehicle_id}"))

    if vehicle_type == "bike":
        vehicle: Vehicle = Bike(
            vehicle_id=vehicle_id,
            frame_number=frame_number,
            has_child_seat=bool(data.get("has_child_seat", False)),
            status=status,
        )
    elif vehicle_type == "ebike":
        vehicle = EBike(
            vehicle_id=vehicle_id,
            frame_number=frame_number,
            battery_health=int(data.get("battery_health", 100)),
            status=status,
        )
    elif vehicle_type == "scooter":
        vehicle = Scooter(
            vehicle_id=vehicle_id,
            frame_number=frame_number,
            battery_health=int(data.get("battery_health", 100)),
            status=status,
        )
    else:
        raise ValueError(f"Invalid vehicle_type in snapshot: {vehicle_type!r}")

    vehicle.rides_since_last_treated = int(data.get("rides_since_last_treated", 0))
    vehicle.has_helmet = bool(data.get("has_helmet", False))

    last_treated = data.get("last_treated_date")
    if isinstance(last_treated, str) and last_treated:
        vehicle._last_treated_date = date.fromisoformat(last_treated)
    else:
        vehicle._last_treated_date = None

    sid = data.get("station_id")
    if sid is not None and isinstance(sid, int):
        vehicle._station_id = sid
    else:
        vehicle._station_id = None

    return vehicle


def _station_to_dict(station: Station) -> dict[str, Any]:
    return {
        "station_id": station.station_id,
        "name": station.name,
        "latitude": station.latitude,
        "longitude": station.longitude,
        "capacity": station.capacity,
        "vehicle_ids": [v._vehicle_id for v in station.vehicles],
    }


def _station_from_dict(data: dict[str, Any]) -> tuple[Station, list[str]]:
    station = Station(
        station_id=int(data["station_id"]),
        name=str(data["name"]),
        latitude=float(data["latitude"]),
        longitude=float(data["longitude"]),
        capacity=int(data["capacity"]),
    )

    vehicle_ids = [str(v_id) for v_id in data.get("vehicle_ids", [])]
    return station, vehicle_ids
