"""Ride domain model."""

from datetime import UTC, datetime
from uuid import uuid4

from tlvflow.domain.enums import RideStatus


class Ride:
    """A ride: a user's use of a vehicle from start to end."""

    # Protected attributes (#)
    _ride_id: str
    _user_id: str
    _vehicle_id: str

    # Private attributes (-)
    __start_time: datetime
    __end_time: datetime | None
    __start_latitude: float
    __start_longitude: float
    __end_latitude: float
    __end_longitude: float
    __distance: float
    __fee: float
    __status: RideStatus

    def __init__(
        self,
        user_id: str,
        vehicle_id: str,
        start_time: datetime,
        *,
        end_time: datetime | None = None,
        start_latitude: float = 0.0,
        start_longitude: float = 0.0,
        end_latitude: float = 0.0,
        end_longitude: float = 0.0,
        distance: float = 0.0,
        fee: float = 0.0,
        ride_id: str | None = None,
    ) -> None:
        """
        Initialize a Ride instance.
        Args:
            ride_id: Unique identifier for the ride
            user_id: ID of the user taking the ride
            vehicle_id: ID of the vehicle used
            start_time: When the ride started (UTC)
            end_time: When the ride ended (UTC), or None if in progress
            start_latitude: Start location latitude
            start_longitude: Start location longitude
            end_latitude: End location latitude
            end_longitude: End location longitude
            distance: Distance travelled
            fee: Ride fee
        """
        self._ride_id = ride_id or uuid4().hex
        self._user_id = self._validate_user_id(user_id)
        self._vehicle_id = self._validate_vehicle_id(vehicle_id)
        self.__start_time = self._validate_datetime(start_time, "start_time")
        self.__end_time = (
            self._validate_datetime(end_time, "end_time")
            if end_time is not None
            else None
        )
        self.__start_latitude = self._validate_float(start_latitude, "start_latitude")
        self.__start_longitude = self._validate_float(
            start_longitude, "start_longitude"
        )
        self.__end_latitude = self._validate_float(end_latitude, "end_latitude")
        self.__end_longitude = self._validate_float(end_longitude, "end_longitude")
        self.__distance = self._validate_float(distance, "distance")
        self.__fee = self._validate_float(fee, "fee")
        self.__status = (
            RideStatus.COMPLETED if self.__end_time is not None else RideStatus.ACTIVE
        )

    @property
    def ride_id(self) -> str:
        return self._ride_id

    @property
    def user_id(self) -> str:
        return self._user_id

    @property
    def vehicle_id(self) -> str:
        return self._vehicle_id

    @property
    def start_time(self) -> datetime:
        return self.__start_time

    @property
    def end_time(self) -> datetime | None:
        return self.__end_time

    @property
    def start_latitude(self) -> float:
        return self.__start_latitude

    @property
    def start_longitude(self) -> float:
        return self.__start_longitude

    @property
    def end_latitude(self) -> float:
        return self.__end_latitude

    @property
    def end_longitude(self) -> float:
        return self.__end_longitude

    @property
    def distance(self) -> float:
        return self.__distance

    @property
    def fee(self) -> float:
        return self.__fee

    def set_fee(self, amount: float) -> None:
        """Set the ride fee (e.g. 0 for degraded/free ride)."""
        self.__fee = self._validate_float(amount, "fee")

    def calculate_fee(self, duration: float, distance: float) -> float:
        """Set and return the ride fee. PDF: constant 15 ILS per ride."""
        self.__distance = distance
        self.__fee = 15.0
        return self.__fee

    def _process_payment(self) -> None:
        """Process payment for the ride (protected)."""
        # Placeholder: integrate with payment system
        pass

    def _log_ride(self) -> None:
        """Log the ride for history/analytics (protected)."""
        # Placeholder: persist or emit ride record
        pass

    def __handle_tracking_error(self) -> None:
        """Handle tracking/location error (private)."""
        # Placeholder: error handling for GPS/tracking
        pass

    def end(self, at: datetime | None = None) -> None:
        """Mark the ride as completed at the given time (UTC)."""
        if self.__end_time is not None:
            raise ValueError("Ride is already ended")
        now = at or datetime.now(UTC)
        if now.tzinfo is None:
            now = now.replace(tzinfo=UTC)
        if now < self.__start_time:
            raise ValueError("end_time cannot be before start_time")
        self.__end_time = now
        self.__status = RideStatus.COMPLETED

    def cancel(self) -> None:
        """Mark the ride as cancelled."""
        if self.__end_time is not None:
            raise ValueError("Ride is already ended")
        if self.__status == RideStatus.CANCELLED:
            raise ValueError("Ride is already cancelled")
        self.__status = RideStatus.CANCELLED

    def status(self) -> RideStatus:
        """Return the current status of the ride."""
        return self.__status

    def is_active(self) -> bool:
        """Return True if the ride is in progress (ACTIVE)."""
        return self.__status == RideStatus.ACTIVE

    @staticmethod
    def _validate_user_id(user_id: str) -> str:
        if not isinstance(user_id, str) or not user_id.strip():
            raise ValueError("user_id must be a non-empty string")
        return user_id.strip()

    @staticmethod
    def _validate_vehicle_id(vehicle_id: str) -> str:
        if not isinstance(vehicle_id, str) or not vehicle_id.strip():
            raise ValueError("vehicle_id must be a non-empty string")
        return vehicle_id.strip()

    @staticmethod
    def _validate_datetime(value: datetime, name: str) -> datetime:
        if not isinstance(value, datetime):
            raise ValueError(f"{name} must be a datetime")
        return value

    @staticmethod
    def _validate_float(value: float, name: str) -> float:
        if not isinstance(value, int | float):
            raise ValueError(f"{name} must be a number")
        return float(value)
