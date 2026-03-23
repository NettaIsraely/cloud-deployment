from __future__ import annotations

from abc import ABC
from datetime import date, datetime
from typing import Any

from tlvflow.domain.enums import TreatmentType, VehicleStatus


class Vehicle(ABC):
    """Abstract base class representing a vehicle in the system."""

    # Protected attributes
    _vehicle_id: str
    _frame_number: str

    # Private attribute
    __status: VehicleStatus

    # Public attributes
    rides_since_last_treated: int
    has_helmet: bool

    # Protected: last treatment date (None if never treated)
    _last_treated_date: date | None

    # Protected: station id when docked (None when not at a station)
    _station_id: int | None

    # Property
    @property
    def is_electric(self) -> bool:
        raise NotImplementedError("Subclasses must implement is_electric property")

    def __init__(
        self,
        vehicle_id: str,
        frame_number: str,
        status: VehicleStatus = VehicleStatus.AVAILABLE,
        *,
        rides_since_last_treated: int = 0,
        last_treated_date: date | datetime | None = None,
    ):
        """
        Initialize a Vehicle instance.

        Args:
            vehicle_id: Unique identifier for the vehicle
            frame_number: Frame/chassis number of the vehicle
            status: Current status of the vehicle (default: AVAILABLE)
            rides_since_last_treated: Number of rides since last treatment (default: 0)
            last_treated_date: Date of last treatment (default: None)
        """
        self._vehicle_id = vehicle_id
        self._frame_number = frame_number
        self.__status = status
        self.rides_since_last_treated = rides_since_last_treated
        self.has_helmet = False
        self._station_id = None
        if last_treated_date is None:
            self._last_treated_date = None
        elif isinstance(last_treated_date, datetime):
            self._last_treated_date = last_treated_date.date()
        else:
            self._last_treated_date = last_treated_date

    def set_status(self, status: VehicleStatus) -> None:
        """Set the vehicle status."""
        self.__status = status

    def is_unrentable(self) -> bool:
        """True if vehicle is unrentable per spec (rides_since_last_treated > 10)."""
        return self.rides_since_last_treated > 10

    def is_treatment_eligible(self) -> bool:
        """True if vehicle is eligible for treatment per spec (rides_since_last_treated >= 7)."""
        return self.rides_since_last_treated >= 7

    def check_maintenance_needed(self, reports: list[Any] | None = None) -> bool:
        """
        Check if the vehicle needs maintenance.

        Maintenance is needed if:
        - 7 or more rides have been done since last treatment (treatment eligibility per spec), OR
        - A user has reported maintenance needed (via VehicleReport)

        Args:
            reports: Optional list of VehicleReport instances to check for user reports

        Returns:
            bool: True if maintenance is needed, False otherwise
        """
        if self.rides_since_last_treated >= 7:
            return True

        if reports:
            for report in reports:
                if (
                    hasattr(report, "_vehicle_id")
                    and report._vehicle_id == self._vehicle_id
                ):
                    return True

        return False

    def complete_maintenance(self) -> None:
        """
        Mark maintenance/treatment as complete. Resets rides_since_last_treated to 0
        and sets last_treated_date to today.
        """
        self.rides_since_last_treated = 0
        self._last_treated_date = date.today()

    def get_required_treatments(self) -> list[TreatmentType]:
        """Return the list of treatments required for this vehicle type."""
        return [TreatmentType.GENERAL_INSPECTION]

    def check_status(self) -> VehicleStatus:
        """
        Check the current status of the vehicle.

        Returns:
            VehicleStatus: The current status of the vehicle
        """
        return self.__status

    @property
    def last_treated_date(self) -> date | None:
        """Return the date of last treatment, or None if never treated."""
        return self._last_treated_date

    @property
    def station_id(self) -> int | None:
        """Station id when docked, or None when not at a station. Set/cleared by Station.dock/undock."""
        return self._station_id

    @property
    def vehicle_id(self) -> str:
        """Unique identifier for the vehicle."""
        return self._vehicle_id

    def vehicle_type(self) -> str:
        """API-facing type string: 'bike' | 'ebike' | 'scooter' for response schemas."""
        name = type(self).__name__
        if name == "Bike":
            return "bike"
        if name == "EBike":
            return "ebike"
        if name == "Scooter":
            return "scooter"
        return "bike"

    def is_rentable(self) -> bool:
        """True if vehicle can be rented: AVAILABLE and rides_since_last_treated <= 10."""
        return (
            self.check_status() == VehicleStatus.AVAILABLE and not self.is_unrentable()
        )


class Bike(Vehicle):
    """Bike subclass representing a regular bicycle."""

    has_child_seat: bool

    def __init__(
        self,
        vehicle_id: str,
        frame_number: str,
        has_child_seat: bool = False,
        status: VehicleStatus = VehicleStatus.AVAILABLE,
    ):
        """
        Initialize a Bike instance.

        Args:
            vehicle_id: Unique identifier for the bike
            frame_number: Frame number of the bike
            has_child_seat: Whether the bike has a child seat (default: False)
            status: Current status of the bike (default: AVAILABLE)
        """
        super().__init__(vehicle_id, frame_number, status)
        self.has_child_seat = has_child_seat

    @property
    def is_electric(self) -> bool:
        return False

    def check_maintenance_needed(self, reports: list[Any] | None = None) -> bool:
        """
        Check if the bike needs maintenance.

        Args:
            reports: Optional list of VehicleReport instances to check for user reports

        Returns:
            bool: True if maintenance is needed (7+ rides since last
                maintenance or user reported), False otherwise
        """
        return super().check_maintenance_needed(reports)

    def get_required_treatments(self) -> list[TreatmentType]:
        return [TreatmentType.CHAIN_LUBRICATION, TreatmentType.GENERAL_INSPECTION]


class EBike(Vehicle):
    """EBike subclass representing an electric bicycle."""

    battery_health: int

    def __init__(
        self,
        vehicle_id: str,
        frame_number: str,
        battery_health: int = 100,
        status: VehicleStatus = VehicleStatus.AVAILABLE,
    ):
        """
        Initialize an EBike instance.

        Args:
            vehicle_id: Unique identifier for the e-bike
            frame_number: Frame number of the e-bike
            battery_health: Battery health percentage (0-100, default: 100)
            status: Current status of the e-bike (default: AVAILABLE)
        """
        super().__init__(vehicle_id, frame_number, status)
        if not 0 <= battery_health <= 100:
            raise ValueError("Battery health must be between 0 and 100")
        self.battery_health = battery_health

    @property
    def is_electric(self) -> bool:
        return True

    def check_maintenance_needed(self, reports: list[Any] | None = None) -> bool:
        """
        Check if the e-bike needs maintenance.

        Args:
            reports: Optional list of VehicleReport instances to check for user reports

        Returns:
            bool: True if maintenance is needed (7+ rides since last
                maintenance, user reported, or low battery), False otherwise
        """
        # Check base maintenance conditions (rides or user report)
        base_maintenance = super().check_maintenance_needed(reports)
        # Also check battery health
        return base_maintenance or self.battery_health < 20


class Scooter(Vehicle):
    """Scooter subclass representing an electric scooter."""

    battery_health: int

    def __init__(
        self,
        vehicle_id: str,
        frame_number: str,
        battery_health: int = 100,
        status: VehicleStatus = VehicleStatus.AVAILABLE,
    ):
        """
        Initialize a Scooter instance.

        Args:
            vehicle_id: Unique identifier for the scooter
            frame_number: Frame number of the scooter
            battery_health: Battery health percentage (0-100, default: 100)
            status: Current status of the scooter (default: AVAILABLE)
        """
        super().__init__(vehicle_id, frame_number, status)
        if not 0 <= battery_health <= 100:
            raise ValueError("Battery health must be between 0 and 100")
        self.battery_health = battery_health

    @property
    def is_electric(self) -> bool:
        return True

    def check_maintenance_needed(self, reports: list[Any] | None = None) -> bool:
        """
        Check if the scooter needs maintenance.

        Args:
            reports: Optional list of VehicleReport instances to check for user reports

        Returns:
            bool: True if maintenance is needed (7+ rides since last
                maintenance, user reported, or low battery), False otherwise
        """
        # Check base maintenance conditions (rides or user report)
        base_maintenance = super().check_maintenance_needed(reports)
        # Also check battery health
        return base_maintenance or self.battery_health < 20

    def get_required_treatments(self) -> list[TreatmentType]:
        return [TreatmentType.BATTERY_INSPECTION, TreatmentType.SCOOTER_FIRMWARE_UPDATE]


class VehicleFactory:
    """
    Factory class responsible for creating Vehicle instances.

    Centralizes vehicle creation logic to:
    - Avoid duplication
    - Decouple object creation from business logic
    - Improve extensibility
    """

    _vehicle_registry: dict[str, type[Vehicle]] = {
        "bike": Bike,
        "ebike": EBike,
        "scooter": Scooter,
    }

    @classmethod
    def create_vehicle(
        cls,
        vehicle_type: str,
        vehicle_id: str,
        frame_number: str,
        *,
        status: VehicleStatus = VehicleStatus.AVAILABLE,
        has_child_seat: bool = False,
        battery_health: int = 100,
    ) -> Vehicle:
        """
        Create and return a Vehicle instance based on vehicle_type.

        Args:
            vehicle_type: Type of vehicle ("bike", "ebike", "scooter")
            vehicle_id: Unique identifier
            frame_number: Frame number
            status: Vehicle status
            has_child_seat: Relevant only for Bike
            battery_health: Relevant only for EBike/Scooter

        Returns:
            Vehicle instance

        Raises:
            ValueError: If vehicle_type is not supported
        """

        normalized_type = vehicle_type.strip().lower()

        if normalized_type not in cls._vehicle_registry:
            raise ValueError(f"Unsupported vehicle type: {vehicle_type}")

        # Explicit type narrowing for mypy
        if normalized_type == "bike":
            return Bike(
                vehicle_id=vehicle_id,
                frame_number=frame_number,
                has_child_seat=has_child_seat,
                status=status,
            )

        if normalized_type == "ebike":
            return EBike(
                vehicle_id=vehicle_id,
                frame_number=frame_number,
                battery_health=battery_health,
                status=status,
            )

        if normalized_type == "scooter":
            return Scooter(
                vehicle_id=vehicle_id,
                frame_number=frame_number,
                battery_health=battery_health,
                status=status,
            )

        # Defensive fallback (should never happen)
        raise ValueError(f"Unsupported vehicle type: {vehicle_type}")
