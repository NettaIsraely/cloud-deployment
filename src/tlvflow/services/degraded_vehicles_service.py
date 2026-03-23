"""Service for marking vehicles as degraded and returning them to stations.

Orchestrates station_repo, vehicle_repo, and degraded_repo so that
repositories do not touch each other.
"""

from __future__ import annotations

import random
from typing import Any

from tlvflow.domain.vehicles import Vehicle
from tlvflow.persistence.degraded_vehicles_repository import (
    DegradedVehiclesRepository,
)
from tlvflow.persistence.in_memory import StationRepository, VehicleRepository


async def mark_degraded(
    station_repo: StationRepository,
    vehicle_repo: VehicleRepository,
    degraded_repo: DegradedVehiclesRepository,
    vehicle_id: str,
) -> Vehicle | None:
    """Remove vehicle from its station and add to degraded set. O(1) via vehicle.station_id.

    Returns the vehicle if found and moved, None if vehicle not found or not at a station.
    """
    if not vehicle_id or not str(vehicle_id).strip():
        return None
    vehicle = vehicle_repo.get_by_id(vehicle_id.strip())
    if vehicle is None:
        return None
    sid = vehicle.station_id
    if sid is None:
        return None
    station = station_repo.get_by_id(sid)
    if station is None:
        return None
    station.undock(vehicle)
    degraded_repo.add(vehicle)
    return vehicle


async def unmark_degraded(
    station_repo: StationRepository,
    degraded_repo: DegradedVehiclesRepository,
    vehicle_id: str,
) -> Vehicle | None:
    """Remove vehicle from degraded set and dock at a random station with capacity.

    Returns the vehicle if found and reassigned, None if not in degraded set.
    Raises ValueError if no station has available capacity.
    """
    vehicle = degraded_repo.remove(vehicle_id)
    if vehicle is None:
        return None
    stations_with_slots = [s for s in station_repo.get_all() if not s.is_full]
    if not stations_with_slots:
        degraded_repo.add(vehicle)
        raise ValueError("No station with available capacity for reassignment")
    station = random.choice(stations_with_slots)
    station.dock(vehicle)
    return vehicle


async def restore_degraded(
    station_repo: StationRepository,
    vehicle_repo: VehicleRepository,
    degraded_repo: DegradedVehiclesRepository,
    snapshot: dict[str, Any],
) -> None:
    """Restore degraded set from snapshot and undock those vehicles from stations."""
    degraded_repo.restore(snapshot, vehicle_repo=vehicle_repo)
    for vehicle in list(degraded_repo.get_all()):
        sid = vehicle.station_id
        if sid is not None:
            station = station_repo.get_by_id(sid)
            if station is not None and vehicle in station.vehicles:
                station.undock(vehicle)
