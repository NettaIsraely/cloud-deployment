"""
Unit tests for tlvflow.domain.vehicles (Vehicle/Bike/EBike/Scooter).
"""

from __future__ import annotations

import pytest

from tlvflow.domain.enums import TreatmentType, VehicleStatus
from tlvflow.domain.vehicles import Bike, EBike, Scooter, Vehicle


# Vehicle is abstract-ish via the is_electric property. We create a minimal
# concrete subclass that DOES NOT override is_electric, to ensure the base property raises.
class _BadVehicle(Vehicle):
    pass


# Minimal report object used to trigger the "user reported maintenance needed"
# branch. It only needs a _vehicle_id attribute.
class _Report:
    def __init__(self, vehicle_id: str):
        self._vehicle_id = vehicle_id


# Report-like object that does NOT have _vehicle_id, to ensure the
# hasattr(report, "_vehicle_id") guard works and does not trigger maintenance.
class _ReportWithoutVehicleId:
    def __init__(self):
        self.some_other_field = "x"


# Verify Vehicle.__init__ initializes fields correctly and check_status()
# returns what was passed in, including a non-default status.
def test_vehicle_init_and_check_status_sets_expected_state() -> None:
    v = Bike(vehicle_id="V1", frame_number="F1", status=VehicleStatus.DEGRADED)

    assert v._vehicle_id == "V1"
    assert v._frame_number == "F1"
    assert v.rides_since_last_treated == 0
    assert v.has_helmet is False
    assert v.last_treated_date is None
    assert v.check_status() == VehicleStatus.DEGRADED

    v.set_status(VehicleStatus.AVAILABLE)
    assert v.check_status() == VehicleStatus.AVAILABLE


# Spec: unrentable at rides_since_last_treated > 10
def test_is_unrentable_when_over_10_rides() -> None:
    b = Bike("B", "FB")
    b.rides_since_last_treated = 10
    assert b.is_unrentable() is False
    b.rides_since_last_treated = 11
    assert b.is_unrentable() is True


# Spec: treatment eligible at >= 7
def test_is_treatment_eligible_at_7_or_more() -> None:
    b = Bike("B", "FB")
    b.rides_since_last_treated = 6
    assert b.is_treatment_eligible() is False
    b.rides_since_last_treated = 7
    assert b.is_treatment_eligible() is True
    b.rides_since_last_treated = 8
    assert b.is_treatment_eligible() is True


# Ensure the base Vehicle.is_electric property raises NotImplementedError
# when not implemented by a subclass.
def test_vehicle_is_electric_base_property_raises() -> None:
    v = _BadVehicle(vehicle_id="V2", frame_number="F2")
    with pytest.raises(NotImplementedError):
        _ = v.is_electric


# Verify Bike's is_electric is False and EBike/Scooter is True.
def test_is_electric_property_per_type() -> None:
    assert Bike("B1", "FB1").is_electric is False
    assert EBike("E1", "FE1").is_electric is True
    assert Scooter("S1", "FS1").is_electric is True


# Cover the "7+ rides since last treatment" branch in Vehicle.check_maintenance_needed (treatment eligibility per spec).
def test_maintenance_needed_when_seven_or_more_rides_since_last_maintenance() -> None:
    b = Bike("B2", "FB2")
    b.rides_since_last_treated = 7

    assert b.check_maintenance_needed() is True


# Cover the "reports is None or empty" path where maintenance is NOT needed.
def test_maintenance_not_needed_when_under_threshold_and_no_reports() -> None:
    b = Bike("B3", "FB3")
    b.rides_since_last_treated = 6

    assert b.check_maintenance_needed() is False
    assert b.check_maintenance_needed([]) is False


# Cover the report loop branch that triggers maintenance when a report matches _vehicle_id.
def test_maintenance_needed_when_matching_report_exists() -> None:
    b = Bike("B4", "FB4")
    b.rides_since_last_treated = 1

    reports = [_Report("OTHER"), _Report("B4")]
    assert b.check_maintenance_needed(reports) is True


# Cover the report loop branch where reports are present but do NOT match,
# including an object without _vehicle_id (hasattr guard).
def test_maintenance_not_needed_when_reports_do_not_match_or_missing_attr() -> None:
    b = Bike("B5", "FB5")
    b.rides_since_last_treated = 1

    reports = [_Report("OTHER"), _ReportWithoutVehicleId()]
    assert b.check_maintenance_needed(reports) is False


# Cover complete_maintenance(), ensuring it resets rides_since_last_treated and sets last_treated_date.
def test_complete_maintenance_resets_maintenance_counter() -> None:
    from datetime import date

    b = Bike("B6", "FB6")
    b.rides_since_last_treated = 12
    assert b.check_maintenance_needed() is True

    b.complete_maintenance()
    assert b.rides_since_last_treated == 0
    assert b.last_treated_date == date.today()
    assert b.check_maintenance_needed() is False

    b.rides_since_last_treated = 6
    assert b.check_maintenance_needed() is False

    b.rides_since_last_treated = 7
    assert b.check_maintenance_needed() is True


# Cover EBike battery validation: values below 0 and above 100 should raise ValueError.
@pytest.mark.parametrize("battery_health", [-1, 101])
def test_ebike_invalid_battery_health_raises(battery_health: int) -> None:
    with pytest.raises(ValueError):
        EBike("E2", "FE2", battery_health=battery_health)


# Cover Scooter battery validation: values below 0 and above 100 should raise ValueError.
@pytest.mark.parametrize("battery_health", [-50, 150])
def test_scooter_invalid_battery_health_raises(battery_health: int) -> None:
    with pytest.raises(ValueError):
        Scooter("S2", "FS2", battery_health=battery_health)


# Cover EBike.check_maintenance_needed battery-based condition:
# if base maintenance is False but battery < 20, it should still return True.
def test_ebike_maintenance_needed_when_battery_low_even_if_base_false() -> None:
    e = EBike("E3", "FE3", battery_health=19)
    e.rides_since_last_treated = 0

    assert e.check_maintenance_needed() is True


# Cover EBike.check_maintenance_needed where base maintenance is True,
# ensuring it returns True regardless of battery health.
def test_ebike_maintenance_needed_when_base_true_even_if_battery_ok() -> None:
    e = EBike("E4", "FE4", battery_health=100)
    e.rides_since_last_treated = 10

    assert e.check_maintenance_needed() is True


# Cover EBike.check_maintenance_needed where both base maintenance is False
# and battery is NOT low, so result should be False.
def test_ebike_maintenance_not_needed_when_base_false_and_battery_ok() -> None:
    e = EBike("E5", "FE5", battery_health=20)
    e.rides_since_last_treated = 3

    assert e.check_maintenance_needed() is False


# Mirror the EBike battery logic tests for Scooter: low battery triggers maintenance.
def test_scooter_maintenance_needed_when_battery_low_even_if_base_false() -> None:
    s = Scooter("S3", "FS3", battery_health=0)
    s.rides_since_last_treated = 0

    assert s.check_maintenance_needed() is True


# Scooter returns True when base maintenance is True, regardless of battery.
def test_scooter_maintenance_needed_when_base_true_even_if_battery_ok() -> None:
    s = Scooter("S4", "FS4", battery_health=100)
    s.rides_since_last_treated = 10

    assert s.check_maintenance_needed() is True


# Scooter returns False when base maintenance is False and battery is not low.
def test_scooter_maintenance_not_needed_when_base_false_and_battery_ok() -> None:
    s = Scooter("S5", "FS5", battery_health=20)
    s.rides_since_last_treated = 2

    assert s.check_maintenance_needed() is False


# --- get_required_treatments() ---


# The base Vehicle implementation (accessed via a concrete subclass that does NOT
# override get_required_treatments) should return only GENERAL_INSPECTION.
class _BaseVehicle(Vehicle):
    @property
    def is_electric(self) -> bool:
        return False


def test_base_vehicle_get_required_treatments_returns_general_inspection() -> None:
    v = _BaseVehicle("V_BASE", "F_BASE")
    assert v.get_required_treatments() == [TreatmentType.GENERAL_INSPECTION]


def test_bike_get_required_treatments_returns_chain_lubrication_and_general_inspection() -> (
    None
):
    b = Bike("B_T1", "FB_T1")
    assert b.get_required_treatments() == [
        TreatmentType.CHAIN_LUBRICATION,
        TreatmentType.GENERAL_INSPECTION,
    ]


def test_ebike_get_required_treatments_returns_general_inspection() -> None:
    e = EBike("E_T1", "FE_T1")
    assert e.get_required_treatments() == [TreatmentType.GENERAL_INSPECTION]


def test_scooter_get_required_treatments_returns_battery_inspection_and_firmware_update() -> (
    None
):
    s = Scooter("S_T1", "FS_T1")
    assert s.get_required_treatments() == [
        TreatmentType.BATTERY_INSPECTION,
        TreatmentType.SCOOTER_FIRMWARE_UPDATE,
    ]
