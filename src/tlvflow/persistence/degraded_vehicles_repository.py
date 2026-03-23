"""In-memory store for user-reported degraded vehicles.

Repositories do not touch each other. A service is responsible for
removing vehicles from stations and returning them (see degraded_vehicles_service).
"""

from __future__ import annotations

from typing import Any

from tlvflow.domain.vehicles import Vehicle
from tlvflow.persistence.in_memory import VehicleRepository


class DegradedVehiclesRepository:
    """In-memory repository for degraded (user-reported) vehicles.

    Only stores and retrieves; does not modify stations or other repos.
    """

    def __init__(self) -> None:
        self._vehicles: dict[str, Vehicle] = {}

    def add(self, vehicle: Vehicle) -> None:
        """Add vehicle to the degraded set."""
        self._vehicles[vehicle._vehicle_id] = vehicle

    def remove(self, vehicle_id: str) -> Vehicle | None:
        """Remove vehicle from the degraded set and return it, or None if not found."""
        if not isinstance(vehicle_id, str) or not vehicle_id.strip():
            return None
        return self._vehicles.pop(vehicle_id.strip(), None)

    def get_all(self) -> list[Vehicle]:
        """Return all degraded vehicles."""
        return list(self._vehicles.values())

    def get_by_id(self, vehicle_id: str) -> Vehicle | None:
        """Return a degraded vehicle by id, or None."""
        if not isinstance(vehicle_id, str) or not vehicle_id.strip():
            return None
        return self._vehicles.get(vehicle_id.strip())

    def clear(self) -> None:
        """Clear the degraded set."""
        self._vehicles.clear()

    def snapshot(self) -> dict[str, Any]:
        """Return a JSON-serializable snapshot (vehicle ids only)."""
        return {"vehicle_ids": list(self._vehicles.keys())}

    def restore(
        self,
        snapshot: dict[str, Any],
        *,
        vehicle_repo: VehicleRepository,
    ) -> None:
        """Populate from snapshot using vehicle_repo to resolve ids. Caller must undock these vehicles from stations."""
        self._vehicles.clear()
        vehicle_ids = snapshot.get("vehicle_ids", [])
        if not isinstance(vehicle_ids, list):
            return
        for vid in vehicle_ids:
            if not isinstance(vid, str) or not vid.strip():
                continue
            vehicle = vehicle_repo.get_by_id(vid.strip())
            if vehicle is not None:
                self._vehicles[vid.strip()] = vehicle
