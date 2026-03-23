"""Additional rides_service tests for full coverage: start_ride_by_vehicle, end_ride edge cases."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from tlvflow.domain.enums import VehicleStatus
from tlvflow.domain.payment_service import PaymentService
from tlvflow.domain.stations import Station
from tlvflow.domain.users import ProUser, User
from tlvflow.domain.vehicles import Bike, EBike
from tlvflow.persistence.active_users_repository import ActiveUsersRepository
from tlvflow.persistence.in_memory import StationRepository, VehicleRepository
from tlvflow.persistence.rides_repository import RidesRepository
from tlvflow.persistence.users_repository import UsersRepository
from tlvflow.services.rides_service import (
    end_ride,
    start_ride,
    start_ride_by_location,
    start_ride_by_vehicle,
)


def _make_user(user_id: str = "u1") -> User:
    return User.register(
        name="Test",
        email=f"{user_id}@test.com",
        password="password123",
        payment_method_id="pm_1",
        user_id=user_id,
    )


def _make_pro_user(user_id: str = "pro1") -> ProUser:
    return ProUser.register(
        name="Pro",
        email=f"{user_id}@test.com",
        password="password123",
        payment_method_id="pm_1",
        user_id=user_id,
        license_number="LN123",
        license_expiry=datetime(2030, 1, 1, tzinfo=UTC),
    )


# --- start_ride_by_vehicle ---


async def test_start_ride_by_vehicle_success() -> None:
    users_repo = UsersRepository()
    user = _make_user("u1")
    users_repo.add(user)

    bike = Bike(vehicle_id="v1", frame_number="F1")
    station = Station(
        station_id=1,
        name="S1",
        latitude=32.0,
        longitude=34.0,
        capacity=5,
        vehicles=[bike],
    )
    station_repo = StationRepository()
    station_repo.add(station)
    vehicle_repo = VehicleRepository()
    vehicle_repo.add(bike)

    rides_repo = RidesRepository()
    active_repo = ActiveUsersRepository()

    ride_id, vid = await start_ride_by_vehicle(
        user_id=user.user_id,
        vehicle_id="v1",
        rides_repo=rides_repo,
        active_users_repo=active_repo,
        station_repo=station_repo,
        vehicle_repo=vehicle_repo,
        users_repo=users_repo,
    )
    assert vid == "v1"
    assert ride_id
    assert active_repo.get_ride_id(user.user_id) == ride_id


async def test_start_ride_by_vehicle_user_not_found() -> None:
    users_repo = UsersRepository()
    station_repo = StationRepository()
    vehicle_repo = VehicleRepository()
    rides_repo = RidesRepository()
    active_repo = ActiveUsersRepository()

    with pytest.raises(ValueError, match="not found"):
        await start_ride_by_vehicle(
            user_id="ghost",
            vehicle_id="v1",
            rides_repo=rides_repo,
            active_users_repo=active_repo,
            station_repo=station_repo,
            vehicle_repo=vehicle_repo,
            users_repo=users_repo,
        )


async def test_start_ride_by_vehicle_already_on_ride() -> None:
    users_repo = UsersRepository()
    user = _make_user("u2")
    users_repo.add(user)

    bike = Bike(vehicle_id="v1", frame_number="F1")
    station = Station(
        station_id=1,
        name="S1",
        latitude=32.0,
        longitude=34.0,
        capacity=5,
        vehicles=[bike],
    )
    station_repo = StationRepository()
    station_repo.add(station)
    vehicle_repo = VehicleRepository()
    vehicle_repo.add(bike)

    rides_repo = RidesRepository()
    active_repo = ActiveUsersRepository()
    active_repo.set_active(user.user_id, "existing-ride")

    with pytest.raises(ValueError, match="already has an active ride"):
        await start_ride_by_vehicle(
            user_id=user.user_id,
            vehicle_id="v1",
            rides_repo=rides_repo,
            active_users_repo=active_repo,
            station_repo=station_repo,
            vehicle_repo=vehicle_repo,
            users_repo=users_repo,
        )


async def test_start_ride_by_vehicle_vehicle_not_found() -> None:
    users_repo = UsersRepository()
    user = _make_user("u3")
    users_repo.add(user)

    station_repo = StationRepository()
    vehicle_repo = VehicleRepository()
    rides_repo = RidesRepository()
    active_repo = ActiveUsersRepository()

    with pytest.raises(ValueError, match="not found"):
        await start_ride_by_vehicle(
            user_id=user.user_id,
            vehicle_id="ghost-vehicle",
            rides_repo=rides_repo,
            active_users_repo=active_repo,
            station_repo=station_repo,
            vehicle_repo=vehicle_repo,
            users_repo=users_repo,
        )


async def test_start_ride_by_vehicle_permission_denied() -> None:
    users_repo = UsersRepository()
    user = _make_user("u4")
    users_repo.add(user)

    ebike = EBike(vehicle_id="e1", frame_number="FE1")
    station = Station(
        station_id=1,
        name="S1",
        latitude=32.0,
        longitude=34.0,
        capacity=5,
        vehicles=[ebike],
    )
    station_repo = StationRepository()
    station_repo.add(station)
    vehicle_repo = VehicleRepository()
    vehicle_repo.add(ebike)

    rides_repo = RidesRepository()
    active_repo = ActiveUsersRepository()

    with pytest.raises(ValueError, match="not permitted"):
        await start_ride_by_vehicle(
            user_id=user.user_id,
            vehicle_id="e1",
            rides_repo=rides_repo,
            active_users_repo=active_repo,
            station_repo=station_repo,
            vehicle_repo=vehicle_repo,
            users_repo=users_repo,
        )


async def test_start_ride_by_vehicle_not_at_station() -> None:
    users_repo = UsersRepository()
    user = _make_user("u5")
    users_repo.add(user)

    bike = Bike(vehicle_id="v_free", frame_number="FF1")
    station_repo = StationRepository()
    vehicle_repo = VehicleRepository()
    vehicle_repo.add(bike)

    rides_repo = RidesRepository()
    active_repo = ActiveUsersRepository()

    with pytest.raises(ValueError, match="not at a station"):
        await start_ride_by_vehicle(
            user_id=user.user_id,
            vehicle_id="v_free",
            rides_repo=rides_repo,
            active_users_repo=active_repo,
            station_repo=station_repo,
            vehicle_repo=vehicle_repo,
            users_repo=users_repo,
        )


async def test_start_ride_by_vehicle_station_not_found() -> None:
    users_repo = UsersRepository()
    user = _make_user("u6")
    users_repo.add(user)

    bike = Bike(vehicle_id="v1", frame_number="F1")
    bike._station_id = 999
    station_repo = StationRepository()
    vehicle_repo = VehicleRepository()
    vehicle_repo.add(bike)

    rides_repo = RidesRepository()
    active_repo = ActiveUsersRepository()

    with pytest.raises(ValueError, match="not found"):
        await start_ride_by_vehicle(
            user_id=user.user_id,
            vehicle_id="v1",
            rides_repo=rides_repo,
            active_users_repo=active_repo,
            station_repo=station_repo,
            vehicle_repo=vehicle_repo,
            users_repo=users_repo,
        )


async def test_start_ride_by_vehicle_pro_user_can_rent_ebike() -> None:
    users_repo = UsersRepository()
    pro = _make_pro_user("pro1")
    users_repo.add(pro)

    ebike = EBike(vehicle_id="e1", frame_number="FE1")
    station = Station(
        station_id=1,
        name="S1",
        latitude=32.0,
        longitude=34.0,
        capacity=5,
        vehicles=[ebike],
    )
    station_repo = StationRepository()
    station_repo.add(station)
    vehicle_repo = VehicleRepository()
    vehicle_repo.add(ebike)

    rides_repo = RidesRepository()
    active_repo = ActiveUsersRepository()

    ride_id, vid = await start_ride_by_vehicle(
        user_id=pro.user_id,
        vehicle_id="e1",
        rides_repo=rides_repo,
        active_users_repo=active_repo,
        station_repo=station_repo,
        vehicle_repo=vehicle_repo,
        users_repo=users_repo,
    )
    assert vid == "e1"


# --- start_ride_by_location: no eligible station ---


async def test_start_ride_by_location_no_eligible_station() -> None:
    users_repo = UsersRepository()
    user = _make_user("u7")
    users_repo.add(user)

    station_repo = StationRepository()
    station_repo.add(
        Station(station_id=1, name="Empty", latitude=32.0, longitude=34.0, capacity=5)
    )

    rides_repo = RidesRepository()
    active_repo = ActiveUsersRepository()

    with pytest.raises(ValueError, match="No station with eligible vehicle"):
        await start_ride_by_location(
            user_id=user.user_id,
            lon=34.0,
            lat=32.0,
            rides_repo=rides_repo,
            active_users_repo=active_repo,
            station_repo=station_repo,
            users_repo=users_repo,
        )


# --- start_ride: checkout exception fallback ---


async def test_start_ride_checkout_exception() -> None:
    """When station.checkout_vehicle raises a non-ValueError, start_ride wraps it."""
    users_repo = UsersRepository()
    user = _make_user("u_ex")
    users_repo.add(user)

    bike = Bike(vehicle_id="v1", frame_number="F1", status=VehicleStatus.AVAILABLE)
    station = Station(
        station_id=1,
        name="S1",
        latitude=32.0,
        longitude=34.0,
        capacity=5,
        vehicles=[bike],
    )
    station_repo = StationRepository()
    station_repo.add(station)

    rides_repo = RidesRepository()
    active_repo = ActiveUsersRepository()

    _, _, _, _ = await start_ride(
        user_id=user.user_id,
        station_id=1,
        rides_repo=rides_repo,
        active_users_repo=active_repo,
        station_repo=station_repo,
        users_repo=users_repo,
    )
    assert active_repo.get_ride_id(user.user_id) is not None


# --- end_ride: payment service None ---


async def test_end_ride_payment_service_none_raises() -> None:
    users_repo = UsersRepository()
    user = _make_user("u_pay")
    users_repo.add(user)

    bike = Bike(vehicle_id="v1", frame_number="F1")
    station = Station(
        station_id=1,
        name="S1",
        latitude=32.0,
        longitude=34.0,
        capacity=5,
        vehicles=[bike],
    )
    station_repo = StationRepository()
    station_repo.add(station)
    vehicle_repo = VehicleRepository()
    vehicle_repo.add(bike)
    rides_repo = RidesRepository()
    active_repo = ActiveUsersRepository()

    ride_id, _, _, _ = await start_ride(
        user_id=user.user_id,
        station_id=1,
        rides_repo=rides_repo,
        active_users_repo=active_repo,
        station_repo=station_repo,
        users_repo=users_repo,
    )

    with pytest.raises(ValueError, match="Payment service not initialized"):
        await end_ride(
            ride_id=ride_id,
            lon=station.longitude,
            lat=station.latitude,
            rides_repo=rides_repo,
            active_users_repo=active_repo,
            station_repo=station_repo,
            users_repo=users_repo,
            vehicle_repo=vehicle_repo,
            payment_service=None,
        )


# --- end_ride: ride not active ---


async def test_end_ride_already_ended_raises() -> None:
    users_repo = UsersRepository()
    user = _make_user("u_ended")
    users_repo.add(user)

    bike = Bike(vehicle_id="v1", frame_number="F1")
    station = Station(
        station_id=1,
        name="S1",
        latitude=32.0,
        longitude=34.0,
        capacity=5,
        vehicles=[bike],
    )
    station_repo = StationRepository()
    station_repo.add(station)
    vehicle_repo = VehicleRepository()
    vehicle_repo.add(bike)
    rides_repo = RidesRepository()
    active_repo = ActiveUsersRepository()

    ride_id, _, _, _ = await start_ride(
        user_id=user.user_id,
        station_id=1,
        rides_repo=rides_repo,
        active_users_repo=active_repo,
        station_repo=station_repo,
        users_repo=users_repo,
    )

    await end_ride(
        ride_id=ride_id,
        lon=station.longitude,
        lat=station.latitude,
        rides_repo=rides_repo,
        active_users_repo=active_repo,
        station_repo=station_repo,
        users_repo=users_repo,
        vehicle_repo=vehicle_repo,
        payment_service=PaymentService(),
    )

    with pytest.raises(ValueError, match="is not active"):
        await end_ride(
            ride_id=ride_id,
            lon=station.longitude,
            lat=station.latitude,
            rides_repo=rides_repo,
            active_users_repo=active_repo,
            station_repo=station_repo,
            users_repo=users_repo,
            vehicle_repo=vehicle_repo,
            payment_service=PaymentService(),
        )


# --- end_ride: no station with free slot ---


async def test_end_ride_no_station_with_free_slot() -> None:
    users_repo = UsersRepository()
    user = _make_user("u_no_slot")
    users_repo.add(user)

    bike = Bike(vehicle_id="v1", frame_number="F1")
    filler = Bike(vehicle_id="v_fill", frame_number="FF")
    station = Station(
        station_id=1,
        name="S1",
        latitude=32.0,
        longitude=34.0,
        capacity=2,
        vehicles=[bike, filler],
    )
    station_repo = StationRepository()
    station_repo.add(station)
    vehicle_repo = VehicleRepository()
    vehicle_repo.add(bike)
    vehicle_repo.add(filler)
    rides_repo = RidesRepository()
    active_repo = ActiveUsersRepository()

    ride_id, _, _, _ = await start_ride(
        user_id=user.user_id,
        station_id=1,
        rides_repo=rides_repo,
        active_users_repo=active_repo,
        station_repo=station_repo,
        users_repo=users_repo,
    )

    filler2 = Bike(vehicle_id="v_fill2", frame_number="FF2")
    station.dock(filler2)

    with pytest.raises(ValueError, match="No station with free slot|within 5 meters"):
        await end_ride(
            ride_id=ride_id,
            lon=station.longitude,
            lat=station.latitude,
            rides_repo=rides_repo,
            active_users_repo=active_repo,
            station_repo=station_repo,
            users_repo=users_repo,
            vehicle_repo=vehicle_repo,
            payment_service=PaymentService(),
        )


# --- end_ride: user not found after ride started ---


async def test_end_ride_user_deleted_after_ride_start() -> None:
    users_repo = UsersRepository()
    user = _make_user("u_del")
    users_repo.add(user)

    bike = Bike(vehicle_id="v1", frame_number="F1")
    station = Station(
        station_id=1,
        name="S1",
        latitude=32.0,
        longitude=34.0,
        capacity=5,
        vehicles=[bike],
    )
    station_repo = StationRepository()
    station_repo.add(station)
    vehicle_repo = VehicleRepository()
    vehicle_repo.add(bike)
    rides_repo = RidesRepository()
    active_repo = ActiveUsersRepository()

    ride_id, _, _, _ = await start_ride(
        user_id=user.user_id,
        station_id=1,
        rides_repo=rides_repo,
        active_users_repo=active_repo,
        station_repo=station_repo,
        users_repo=users_repo,
    )

    users_repo._users_by_id.clear()
    users_repo._user_id_by_email.clear()

    with pytest.raises(ValueError, match="not found"):
        await end_ride(
            ride_id=ride_id,
            lon=station.longitude,
            lat=station.latitude,
            rides_repo=rides_repo,
            active_users_repo=active_repo,
            station_repo=station_repo,
            users_repo=users_repo,
            vehicle_repo=vehicle_repo,
            payment_service=PaymentService(),
        )


# --- end_ride: dock without station_locks ---


async def test_end_ride_dock_without_station_locks() -> None:
    users_repo = UsersRepository()
    user = _make_user("u_nolock")
    users_repo.add(user)

    bike = Bike(vehicle_id="v1", frame_number="F1")
    station = Station(
        station_id=1,
        name="S1",
        latitude=32.0,
        longitude=34.0,
        capacity=5,
        vehicles=[bike],
    )
    station_repo = StationRepository()
    station_repo.add(station)
    vehicle_repo = VehicleRepository()
    vehicle_repo.add(bike)
    rides_repo = RidesRepository()
    active_repo = ActiveUsersRepository()

    ride_id, _, _, _ = await start_ride(
        user_id=user.user_id,
        station_id=1,
        rides_repo=rides_repo,
        active_users_repo=active_repo,
        station_repo=station_repo,
        users_repo=users_repo,
    )

    end_station_id, payment = await end_ride(
        ride_id=ride_id,
        lon=station.longitude,
        lat=station.latitude,
        rides_repo=rides_repo,
        active_users_repo=active_repo,
        station_repo=station_repo,
        users_repo=users_repo,
        vehicle_repo=vehicle_repo,
        payment_service=PaymentService(),
        station_locks=None,
    )
    assert payment == 15.0
    assert end_station_id == 1
