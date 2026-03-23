"""Link vehicles to stations during startup.

After loading vehicle_repo and station_repo, call link_vehicles_to_stations
to dock each vehicle into its station by station_id. Handles: station full,
station not found, degraded vehicles (go to degraded repo instead).
"""

from __future__ import annotations

import logging

from tlvflow.domain.enums import VehicleStatus
from tlvflow.persistence.degraded_vehicles_repository import (
    DegradedVehiclesRepository,
)
from tlvflow.persistence.in_memory import StationRepository, VehicleRepository

logger = logging.getLogger(__name__)


async def link_vehicles_to_stations(
    vehicle_repo: VehicleRepository,
    station_repo: StationRepository,
    degraded_repo: DegradedVehiclesRepository,
) -> None:
    """Dock each vehicle into its station by station_id. Degraded vehicles go to degraded_repo.

    Edge cases:
    - Station not found: log warning, skip docking.
    - Station full: log warning, skip docking.
    - Vehicle status DEGRADED: add to degraded_repo, do not dock.
    - Vehicle has no station_id: log warning, skip.
    """
    for vehicle in vehicle_repo.get_all():
        if vehicle.check_status() == VehicleStatus.DEGRADED:
            degraded_repo.add(vehicle)
            vehicle._station_id = (
                None  # degraded = not at a station; avoid undock in restore_degraded
            )
            continue
        sid = vehicle.station_id
        if sid is None:
            logger.warning(
                "Vehicle %s has no station_id, skipping dock",
                vehicle.vehicle_id,
            )
            continue
        station = station_repo.get_by_id(sid)
        if station is None:
            logger.warning(
                "Station %s not found for vehicle %s, skipping dock",
                sid,
                vehicle.vehicle_id,
            )
            continue
        if station.is_full:
            logger.warning(
                "Station %s is full, cannot dock vehicle %s",
                sid,
                vehicle.vehicle_id,
            )
            continue
        station.dock(vehicle)
