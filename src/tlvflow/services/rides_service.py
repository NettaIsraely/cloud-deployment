from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from tlvflow.domain.enums import VehicleStatus
from tlvflow.domain.rides import Ride
from tlvflow.persistence.active_users_repository import ActiveUsersRepository
from tlvflow.persistence.in_memory import StationRepository, VehicleRepository
from tlvflow.persistence.rides_repository import RidesRepository
from tlvflow.persistence.users_repository import UsersRepository
from tlvflow.services.stations_service import (
    distance_meters,
    find_nearest_station_with_eligible_vehicle,
    find_nearest_station_with_free_slot,
)

if TYPE_CHECKING:
    from tlvflow.domain.payment_service import PaymentService

_PERMISSION_DENIED_MSG = (
    "You are not permitted to rent this vehicle. Upgrade to Pro for electric vehicles."
)


async def start_ride_by_vehicle(
    user_id: str,
    vehicle_id: str,
    rides_repo: RidesRepository,
    active_users_repo: ActiveUsersRepository,
    station_repo: StationRepository,
    vehicle_repo: VehicleRepository,
    users_repo: UsersRepository,
) -> tuple[str, str]:
    """
    Start a ride by vehicle id (user scans/enters vehicle number). The vehicle must be
    at a station. Checks user.can_rent(vehicle); raises with _PERMISSION_DENIED_MSG if not allowed.
    """
    user = users_repo.get_by_id(user_id)
    if not user:
        raise ValueError(f"User {user_id} not found")
    if active_users_repo.get_ride_id(user_id) is not None:
        raise ValueError("User already has an active ride")

    vehicle = vehicle_repo.get_by_id(vehicle_id)
    if not vehicle:
        raise ValueError(f"Vehicle {vehicle_id} not found")
    if not user.can_rent(vehicle):
        raise ValueError(_PERMISSION_DENIED_MSG)
    sid = vehicle.station_id
    if sid is None:
        raise ValueError(f"Vehicle {vehicle_id} is not at a station")

    station = station_repo.get_by_id(sid)
    if not station:
        raise ValueError(f"Station {sid} not found")
    try:
        station.checkout_vehicle_by_id(vehicle_id)
    except ValueError as e:
        raise ValueError(str(e)) from e

    ride = Ride(
        user_id=user_id,
        vehicle_id=vehicle_id,
        start_time=datetime.now(UTC),
        start_latitude=station.latitude,
        start_longitude=station.longitude,
    )
    rides_repo.add(ride)
    active_users_repo.set_active(user_id, ride.ride_id)
    return (ride.ride_id, vehicle_id)


async def start_ride_by_location(
    user_id: str,
    lon: float,
    lat: float,
    rides_repo: RidesRepository,
    active_users_repo: ActiveUsersRepository,
    station_repo: StationRepository,
    users_repo: UsersRepository,
    station_locks: defaultdict[int, asyncio.Lock] | None = None,
) -> tuple[str, str, str, int]:
    """
    Start a ride from user location (PDF spec): find nearest station with an eligible
    vehicle, checkout that vehicle, create ride. Returns (ride_id, vehicle_id, vehicle_type, start_station_id).
    """
    user = users_repo.get_by_id(user_id)
    if not user:
        raise ValueError(f"User {user_id} not found")
    if active_users_repo.get_ride_id(user_id) is not None:
        raise ValueError("User already has an active ride")

    result = await find_nearest_station_with_eligible_vehicle(
        station_repo,
        lon=lon,
        lat=lat,
        station_locks=station_locks,
    )
    if result is None:
        raise ValueError("No station with eligible vehicle found")

    station, vehicle = result
    vehicle.set_status(VehicleStatus.IN_USE)

    ride = Ride(
        user_id=user_id,
        vehicle_id=vehicle.vehicle_id,
        start_time=datetime.now(UTC),
        start_latitude=station.latitude,
        start_longitude=station.longitude,
    )
    rides_repo.add(ride)
    active_users_repo.set_active(user_id, ride.ride_id)

    return (
        ride.ride_id,
        vehicle.vehicle_id,
        vehicle.vehicle_type(),
        station.station_id,
    )


async def start_ride(
    user_id: str,
    station_id: int,
    rides_repo: RidesRepository,
    active_users_repo: ActiveUsersRepository,
    station_repo: StationRepository,
    users_repo: UsersRepository,
) -> tuple[str, str, str, int]:
    """
    Start a new ride from a specific station: checkout a vehicle, set IN_USE.

    Returns:
        (ride_id, vehicle_id, vehicle_type, start_station_id).
    """
    user = users_repo.get_by_id(user_id)
    if not user:
        raise ValueError(f"User {user_id} not found")

    if active_users_repo.get_ride_id(user_id) is not None:
        raise ValueError("User already has an active ride")

    station = station_repo.get_by_id(station_id)
    if not station:
        raise ValueError(f"Station {station_id} not found")

    if station.is_empty:
        raise ValueError(f"Station {station_id} has no available vehicles")

    try:
        vehicle = station.checkout_vehicle()
    except Exception as e:
        raise ValueError(f"Failed to checkout vehicle: {str(e)}") from e

    vehicle.set_status(VehicleStatus.IN_USE)

    ride = Ride(
        user_id=user_id,
        vehicle_id=vehicle.vehicle_id,
        start_time=datetime.now(UTC),
        start_latitude=station.latitude,
        start_longitude=station.longitude,
    )

    rides_repo.add(ride)
    active_users_repo.set_active(user_id, ride.ride_id)

    return (
        ride.ride_id,
        vehicle.vehicle_id,
        vehicle.vehicle_type(),
        station.station_id,
    )


async def end_ride(
    ride_id: str,
    lon: float,
    lat: float,
    rides_repo: RidesRepository,
    active_users_repo: ActiveUsersRepository,
    station_repo: StationRepository,
    users_repo: UsersRepository,
    vehicle_repo: VehicleRepository,
    payment_service: PaymentService | None,
    station_locks: defaultdict[int, asyncio.Lock] | None = None,
) -> tuple[int, float]:
    """
    End ride by ride_id: find nearest station with free slot, dock vehicle, charge 15 ILS.

    Returns:
        (end_station_id, payment_charged).
    """
    if payment_service is None:
        raise ValueError("Payment service not initialized")

    ride = rides_repo.get_by_id(ride_id)
    if not ride:
        raise ValueError(f"Ride {ride_id} not found")
    if not ride.is_active():
        raise ValueError(f"Ride {ride_id} is not active")

    user_id = ride.user_id
    vehicle_id = ride.vehicle_id

    station = await find_nearest_station_with_free_slot(
        station_repo,
        lon=lon,
        lat=lat,
    )
    if station is None:
        raise ValueError("No station with free slot found")

    if distance_meters(station, lon, lat) > 5.0:
        raise ValueError("Location must be within 5 meters of a station to end ride")

    end_time = datetime.now(UTC)
    ride.end(at=end_time)
    ride.calculate_fee(duration=0.0, distance=0.0)  # sets fee to 15.0

    user = users_repo.get_by_id(user_id)
    if not user:
        raise ValueError(f"User {user_id} not found")
    await payment_service.process_charge(
        ride_id=ride.ride_id,
        amount=15.0,
        payment_method_id=user.payment_method_id,
    )

    vehicle = vehicle_repo.get_by_id(vehicle_id)
    if vehicle:
        if station_locks is not None:
            async with station_locks[station.station_id]:
                st = station_repo.get_by_id(station.station_id)
                if st is None:
                    raise ValueError(f"Station {station.station_id} not found")
                if st.is_full:
                    raise ValueError("No station with free slot found")
                st.dock(vehicle)
        else:
            station.dock(vehicle)
        vehicle.set_status(VehicleStatus.AVAILABLE)
        vehicle.rides_since_last_treated += 1

    active_users_repo.clear(user_id)

    return (station.station_id, 15.0)
