from tlvflow.domain.enums import VehicleStatus
from tlvflow.domain.vehicles import Vehicle


class Station:
    """Represents a physical station that holds vehicles."""

    _station_id: int
    _name: str
    _latitude: float
    _longitude: float
    _capacity: int
    _vehicles: list[Vehicle]

    def __init__(
        self,
        station_id: int,
        name: str,
        latitude: float,
        longitude: float,
        capacity: int,
        *,
        vehicles: list[Vehicle] | None = None,
    ) -> None:

        self._station_id = self._validate_station_id(station_id)
        self._name = self._validate_name(name)
        self._latitude = self._validate_latitude(latitude)
        self._longitude = self._validate_longitude(longitude)
        self._capacity = self._validate_capacity(capacity)

        self._vehicles = list(vehicles) if vehicles else []
        if len(self._vehicles) > self._capacity:
            raise ValueError("initial vehicles cannot exceed capacity")
        for v in self._vehicles:
            v._station_id = self._station_id

    # properties
    @property
    def station_id(self) -> int:
        return self._station_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def latitude(self) -> float:
        return self._latitude

    @property
    def longitude(self) -> float:
        return self._longitude

    @property
    def capacity(self) -> int:
        return self._capacity

    @property
    def available_slots(self) -> int:
        return self._capacity - len(self._vehicles)

    @property
    def is_full(self) -> bool:
        return self.available_slots == 0

    @property
    def is_empty(self) -> bool:
        return len(self._vehicles) == 0

    @property
    def vehicles(self) -> tuple[Vehicle, ...]:
        return tuple(self._vehicles)

    def has_eligible_vehicle(self) -> bool:
        """True if at least one vehicle is rentable (AVAILABLE and rides_since_last_treated <= 10)."""
        return any(
            v.check_status() == VehicleStatus.AVAILABLE and not v.is_unrentable()
            for v in self._vehicles
        )

    # domain actions
    def dock(self, vehicle: Vehicle) -> None:
        if self.is_full:
            raise ValueError("station is full")
        self._vehicles.append(vehicle)
        vehicle._station_id = self._station_id

    def undock(self, vehicle: Vehicle) -> None:
        try:
            self._vehicles.remove(vehicle)
        except ValueError as exc:
            raise ValueError("vehicle is not in this station") from exc
        vehicle._station_id = None

    def checkout_vehicle(self) -> Vehicle:
        if self.is_empty:
            raise ValueError("Station is empty")
        vehicle = self._vehicles.pop()
        vehicle._station_id = None
        return vehicle

    def checkout_eligible_vehicle(self) -> Vehicle:
        """
        Check out one eligible vehicle using deterministic selection.
        Eligible: status == AVAILABLE and rides_since_last_treated <= 10.
        Selection rule (documented): prefer bike, then ebike, then scooter; tie-break by vehicle_id.
        """
        eligible = [
            v
            for v in self._vehicles
            if v.check_status() == VehicleStatus.AVAILABLE and not v.is_unrentable()
        ]
        if not eligible:
            raise ValueError("Station has no eligible vehicle")
        # Deterministic: type order bike=0, ebike=1, scooter=2, then vehicle_id
        type_order = {"bike": 0, "ebike": 1, "scooter": 2}

        def sort_key(v: Vehicle) -> tuple[int, str]:
            return (type_order.get(v.vehicle_type(), 99), v.vehicle_id)

        chosen = min(eligible, key=sort_key)
        self._vehicles.remove(chosen)
        chosen._station_id = None
        return chosen

    def checkout_vehicle_by_id(self, vehicle_id: str) -> Vehicle:
        """Check out a specific vehicle by id from this station. Raises if not found."""
        if not isinstance(vehicle_id, str) or not vehicle_id.strip():
            raise ValueError("vehicle_id must be a non-empty string")
        vid = vehicle_id.strip()
        for i, v in enumerate(self._vehicles):
            if v.vehicle_id == vid:
                vehicle = self._vehicles.pop(i)
                vehicle._station_id = None
                return vehicle
        raise ValueError(f"Vehicle {vehicle_id} is not at this station")

    # validation
    @staticmethod
    def _validate_station_id(station_id: int) -> int:
        if not isinstance(station_id, int) or station_id < 0:
            raise ValueError("station_id must be a non-negative integer")
        return station_id

    @staticmethod
    def _validate_name(name: str) -> str:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("name must be a non-empty string")
        return name.strip()

    @staticmethod
    def _validate_latitude(latitude: float) -> float:
        lat = float(latitude)
        if not (-90.0 <= lat <= 90.0):
            raise ValueError("latitude must be between -90 and 90")
        return lat

    @staticmethod
    def _validate_longitude(longitude: float) -> float:
        # Tel Aviv is roughly 34.7 - 34.9 lon [cite: 33]
        lon = float(longitude)
        if not (-180.0 <= lon <= 180.0):
            raise ValueError("longitude must be between -180 and 180")
        return lon

    @staticmethod
    def _validate_capacity(capacity: int) -> int:
        if not isinstance(capacity, int) or capacity <= 0:
            raise ValueError("capacity must be a positive integer")
        return capacity
