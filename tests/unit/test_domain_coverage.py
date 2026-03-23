"""Tests to cover remaining domain model gaps"""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from tlvflow.domain.enums import PaymentKind, VehicleStatus
from tlvflow.domain.payment import Payment
from tlvflow.domain.rides import Ride
from tlvflow.domain.stations import Station
from tlvflow.domain.users import ProUser, User
from tlvflow.domain.vehicles import (
    Bike,
    EBike,
    Scooter,
    Vehicle,
    VehicleFactory,
)

# --- Vehicle: last_treated_date with datetime (lines 62-65) ---


def test_vehicle_init_with_datetime_last_treated() -> None:
    dt = datetime(2024, 6, 15, 10, 30, tzinfo=UTC)
    bike = Bike(vehicle_id="v1", frame_number="F1")
    bike._last_treated_date = dt.date()
    assert bike.last_treated_date == date(2024, 6, 15)


def test_vehicle_init_last_treated_date_as_date() -> None:
    from tlvflow.domain.vehicles import VehicleStatus

    bike = Bike.__new__(Bike)
    Vehicle.__init__(
        bike,
        vehicle_id="v_date",
        frame_number="F_date",
        status=VehicleStatus.AVAILABLE,
        last_treated_date=date(2024, 3, 10),
    )
    bike.has_child_seat = False
    assert bike.last_treated_date == date(2024, 3, 10)


def test_vehicle_init_last_treated_date_as_datetime() -> None:
    from tlvflow.domain.vehicles import VehicleStatus

    bike = Bike.__new__(Bike)
    Vehicle.__init__(
        bike,
        vehicle_id="v_dt",
        frame_number="F_dt",
        status=VehicleStatus.AVAILABLE,
        last_treated_date=datetime(2024, 5, 20, 12, 0, tzinfo=UTC),
    )
    bike.has_child_seat = False
    assert bike.last_treated_date == date(2024, 5, 20)


# --- Vehicle.vehicle_type() for Scooter (line 151) ---


def test_scooter_vehicle_type() -> None:
    s = Scooter(vehicle_id="s1", frame_number="FS1")
    assert s.vehicle_type() == "scooter"


def test_ebike_vehicle_type() -> None:
    e = EBike(vehicle_id="e1", frame_number="FE1")
    assert e.vehicle_type() == "ebike"


# --- Vehicle.is_rentable() negative paths (line 155) ---


def test_vehicle_not_rentable_when_in_use() -> None:
    bike = Bike(vehicle_id="v1", frame_number="F1", status=VehicleStatus.IN_USE)
    assert not bike.is_rentable()


def test_vehicle_not_rentable_when_too_many_rides() -> None:
    bike = Bike(vehicle_id="v1", frame_number="F1")
    bike.rides_since_last_treated = 11
    assert not bike.is_rentable()


def test_vehicle_rentable_when_available() -> None:
    bike = Bike(vehicle_id="v1", frame_number="F1")
    bike.rides_since_last_treated = 5
    assert bike.is_rentable()


# --- VehicleFactory (lines 347-378) ---


def test_vehicle_factory_create_bike() -> None:
    v = VehicleFactory.create_vehicle("bike", "v1", "F1", has_child_seat=True)
    assert isinstance(v, Bike)
    assert v.has_child_seat is True


def test_vehicle_factory_create_ebike() -> None:
    v = VehicleFactory.create_vehicle("ebike", "v2", "F2", battery_health=80)
    assert isinstance(v, EBike)
    assert v.battery_health == 80


def test_vehicle_factory_create_scooter() -> None:
    v = VehicleFactory.create_vehicle("scooter", "v3", "F3", battery_health=90)
    assert isinstance(v, Scooter)
    assert v.battery_health == 90


def test_vehicle_factory_unsupported_type() -> None:
    with pytest.raises(ValueError, match="Unsupported vehicle type"):
        VehicleFactory.create_vehicle("hoverboard", "v4", "F4")


def test_vehicle_factory_normalizes_type() -> None:
    v = VehicleFactory.create_vehicle("  Bike  ", "v5", "F5")
    assert isinstance(v, Bike)


def test_vehicle_factory_with_status() -> None:
    v = VehicleFactory.create_vehicle("ebike", "v6", "F6", status=VehicleStatus.IN_USE)
    assert v.check_status() == VehicleStatus.IN_USE


# --- Station.checkout_eligible_vehicle (line 115) ---


def test_station_checkout_eligible_vehicle_no_eligible() -> None:
    bike = Bike(vehicle_id="v1", frame_number="F1", status=VehicleStatus.IN_USE)
    station = Station(
        station_id=1,
        name="A",
        latitude=32.0,
        longitude=34.0,
        capacity=5,
        vehicles=[bike],
    )
    with pytest.raises(ValueError, match="no eligible vehicle"):
        station.checkout_eligible_vehicle()


def test_station_checkout_eligible_vehicle_success() -> None:
    bike = Bike(vehicle_id="v1", frame_number="F1")
    station = Station(
        station_id=1,
        name="A",
        latitude=32.0,
        longitude=34.0,
        capacity=5,
        vehicles=[bike],
    )
    v = station.checkout_eligible_vehicle()
    assert v.vehicle_id == "v1"
    assert station.is_empty


def test_station_checkout_eligible_prefers_bike_over_ebike() -> None:
    ebike = EBike(vehicle_id="e1", frame_number="FE1")
    bike = Bike(vehicle_id="b1", frame_number="FB1")
    station = Station(
        station_id=1,
        name="A",
        latitude=32.0,
        longitude=34.0,
        capacity=5,
        vehicles=[ebike, bike],
    )
    v = station.checkout_eligible_vehicle()
    assert v.vehicle_id == "b1"


# --- Station.checkout_vehicle_by_id (lines 129-137) ---


def test_station_checkout_vehicle_by_id_success() -> None:
    bike = Bike(vehicle_id="v1", frame_number="F1")
    station = Station(
        station_id=1,
        name="A",
        latitude=32.0,
        longitude=34.0,
        capacity=5,
        vehicles=[bike],
    )
    v = station.checkout_vehicle_by_id("v1")
    assert v.vehicle_id == "v1"
    assert station.is_empty


def test_station_checkout_vehicle_by_id_not_found() -> None:
    bike = Bike(vehicle_id="v1", frame_number="F1")
    station = Station(
        station_id=1,
        name="A",
        latitude=32.0,
        longitude=34.0,
        capacity=5,
        vehicles=[bike],
    )
    with pytest.raises(ValueError, match="not at this station"):
        station.checkout_vehicle_by_id("v999")


def test_station_checkout_vehicle_by_id_empty_string() -> None:
    station = Station(station_id=1, name="A", latitude=32.0, longitude=34.0, capacity=5)
    with pytest.raises(ValueError, match="non-empty string"):
        station.checkout_vehicle_by_id("")


def test_station_checkout_vehicle_by_id_whitespace() -> None:
    station = Station(station_id=1, name="A", latitude=32.0, longitude=34.0, capacity=5)
    with pytest.raises(ValueError, match="non-empty string"):
        station.checkout_vehicle_by_id("   ")


# --- Station.checkout_vehicle on empty (line 98) ---


def test_station_checkout_vehicle_empty_station() -> None:
    station = Station(station_id=1, name="A", latitude=32.0, longitude=34.0, capacity=5)
    with pytest.raises(ValueError, match="empty"):
        station.checkout_vehicle()


# --- User.upgrade_to_pro (lines 155-167) ---


def test_user_upgrade_to_pro_preserves_state() -> None:
    user = User.register(
        name="Test",
        email="test@example.com",
        password="password123",
        payment_method_id="pm_1",
        user_id="u1",
    )
    user.start_ride("v1")
    user.set_current_ride("mock-ride")

    pro = user.upgrade_to_pro(
        license_number="LN123",
        license_expiry=datetime(2030, 1, 1, tzinfo=UTC),
    )
    assert isinstance(pro, ProUser)
    assert pro.user_id == "u1"
    assert pro._current_ride == "mock-ride"
    assert pro._current_vehicle_id == "v1"
    assert pro._ride_history == []


# --- User.update_payment_method (line 193) ---


def test_user_update_payment_method() -> None:
    user = User.register(
        name="Test",
        email="test@example.com",
        password="password123",
        payment_method_id="pm_old",
    )
    user.update_payment_method("pm_new")
    assert user.payment_method_id == "pm_new"


# --- ProUser.validate_license with naive datetime (lines 347, 350) ---


def test_pro_user_validate_license_naive_datetime() -> None:
    pro = ProUser.register(
        name="Pro",
        email="pro@test.com",
        password="password123",
        payment_method_id="pm_1",
        license_number="LN123",
        license_expiry=datetime(2030, 1, 1),  # naive
    )
    assert pro.validate_license(at=datetime(2025, 1, 1)) is True
    assert pro.validate_license(at=datetime(2031, 1, 1)) is False


def test_pro_user_validate_license_utc_datetime() -> None:
    pro = ProUser.register(
        name="Pro",
        email="pro2@test.com",
        password="password123",
        payment_method_id="pm_1",
        license_number="LN456",
        license_expiry=datetime(2030, 1, 1, tzinfo=UTC),
    )
    assert pro.validate_license(at=datetime(2025, 1, 1, tzinfo=UTC)) is True


# --- Ride._process_payment, _log_ride, __handle_tracking_error (lines 136, 141, 146) ---


def test_ride_process_payment_noop() -> None:
    ride = Ride(user_id="u1", vehicle_id="v1", start_time=datetime.now(UTC))
    ride._process_payment()


def test_ride_log_ride_noop() -> None:
    ride = Ride(user_id="u1", vehicle_id="v1", start_time=datetime.now(UTC))
    ride._log_ride()


def test_ride_handle_tracking_error_noop() -> None:
    ride = Ride(user_id="u1", vehicle_id="v1", start_time=datetime.now(UTC))
    ride._Ride__handle_tracking_error()


# --- Ride.end() with naive datetime (line 154) ---


def test_ride_end_with_naive_datetime() -> None:
    ride = Ride(
        user_id="u1",
        vehicle_id="v1",
        start_time=datetime(2025, 1, 1, tzinfo=UTC),
    )
    ride.end(at=datetime(2025, 1, 2))  # naive datetime
    assert ride.end_time is not None


# --- Payment validations (lines 46, 52, 58) ---


def test_payment_invalid_ride_id() -> None:
    with pytest.raises(ValueError, match="ride_id must be a non-empty string"):
        Payment(
            ride_id="",
            amount=15.0,
            payment_method_id="pm_1",
            kind=PaymentKind.CHARGE,
        )


def test_payment_invalid_amount() -> None:
    with pytest.raises(ValueError, match="amount must be a positive number"):
        Payment(
            ride_id="r1",
            amount=0,
            payment_method_id="pm_1",
            kind=PaymentKind.CHARGE,
        )


def test_payment_invalid_payment_method_id() -> None:
    with pytest.raises(
        ValueError, match="payment_method_id must be a non-empty string"
    ):
        Payment(
            ride_id="r1",
            amount=15.0,
            payment_method_id="",
            kind=PaymentKind.CHARGE,
        )
