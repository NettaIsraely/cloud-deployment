from __future__ import annotations

import random
from datetime import UTC, datetime

from tlvflow.domain.enums import VehicleStatus
from tlvflow.domain.maintenance_event import MaintenanceEvent
from tlvflow.persistence.active_users_repository import ActiveUsersRepository
from tlvflow.persistence.degraded_vehicles_repository import DegradedVehiclesRepository
from tlvflow.persistence.in_memory import StationRepository, VehicleRepository
from tlvflow.persistence.rides_repository import RidesRepository
from tlvflow.repositories.interfaces import MaintenanceRepositoryProtocol


async def treat_vehicles(
    vehicles_repo: VehicleRepository,
    stations_repo: StationRepository,
    maintenance_repo: MaintenanceRepositoryProtocol,
    degraded_repo: DegradedVehiclesRepository,
) -> list[str]:
    treated_ids: list[str] = []

    degraded_vehicles = degraded_repo.get_all()
    degraded_ids = {v._vehicle_id for v in degraded_vehicles}

    high_ride_vehicles = [
        v
        for v in vehicles_repo.get_all()
        if v.is_treatment_eligible() and v._vehicle_id not in degraded_ids
    ]

    vehicles_to_treat = degraded_vehicles + high_ride_vehicles

    for vehicle in vehicles_to_treat:
        is_degraded = vehicle._vehicle_id in degraded_ids

        # Retrieve the report_id if the vehicle is degraded (before resetting its status)
        report_id = (
            getattr(vehicle, "report_id", getattr(vehicle, "_report_id", ""))
            if is_degraded
            else ""
        )

        event = MaintenanceEvent(
            vehicle_id=vehicle._vehicle_id,
            report_id=report_id,
            open_time=datetime.now(UTC),
            treatments=vehicle.get_required_treatments(),
        )
        event.close_event()
        maintenance_repo.add(event)

        if is_degraded:
            all_stations = stations_repo.get_all()

            current_station = None
            for station in all_stations:
                if vehicle in station.vehicles:
                    current_station = station
                    break

            candidates = [
                s for s in all_stations if not s.is_full and s is not current_station
            ]

            if candidates:
                new_station = random.choice(candidates)
                if current_station is not None:
                    current_station.undock(vehicle)
                new_station.dock(vehicle)

            degraded_repo.remove(vehicle._vehicle_id)

        # Defer status update to the end per PR review
        vehicle.complete_maintenance()
        vehicle.set_status(VehicleStatus.AVAILABLE)

        treated_ids.append(vehicle._vehicle_id)

    return treated_ids


async def report_degraded_vehicle(
    user_id: str,
    vehicle_id: str,
    rides_repo: RidesRepository,
    vehicles_repo: VehicleRepository,
    degraded_repo: DegradedVehiclesRepository,
    active_users_repo: ActiveUsersRepository,
) -> None:
    """Report a vehicle as degraded during an active ride only. Ends the ride at no charge."""
    rides = rides_repo.get_by_user_id(user_id)
    active_ride = next((r for r in rides if r.is_active()), None)

    if active_ride is None or active_ride.vehicle_id != vehicle_id:
        raise ValueError("no active ride")

    vehicle = vehicles_repo._vehicles.get(vehicle_id)
    if vehicle is None:
        raise LookupError("vehicle not found")
    vehicle.set_status(VehicleStatus.DEGRADED)
    del vehicles_repo._vehicles[vehicle_id]
    degraded_repo.add(vehicle)
    active_ride.end()
    active_ride.set_fee(0.0)
    active_users_repo.clear(user_id)
