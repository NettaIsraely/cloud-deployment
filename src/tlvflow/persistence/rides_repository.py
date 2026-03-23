from __future__ import annotations

from datetime import datetime
from typing import Any

from tlvflow.domain.enums import RideStatus
from tlvflow.domain.rides import Ride


class RidesRepository:
    """In-memory repository for rides, with snapshot/restore for persistence."""

    def __init__(self) -> None:
        self._rides_by_id: dict[str, Ride] = {}
        self._ride_ids_by_user_id: dict[str, list[str]] = {}

    def get_by_id(self, ride_id: str) -> Ride | None:
        if not isinstance(ride_id, str) or not ride_id.strip():
            return None
        return self._rides_by_id.get(ride_id.strip())

    def get_by_user_id(self, user_id: str) -> list[Ride]:
        if not isinstance(user_id, str) or not user_id.strip():
            return []
        ride_ids = self._ride_ids_by_user_id.get(user_id.strip(), [])
        return [self._rides_by_id[rid] for rid in ride_ids if rid in self._rides_by_id]

    def add(self, ride: Ride) -> None:
        self._rides_by_id[ride.ride_id] = ride
        self._ride_ids_by_user_id.setdefault(ride.user_id, []).append(ride.ride_id)

    def snapshot(self) -> dict[str, Any]:
        return {
            ride_id: _ride_to_dict(ride) for ride_id, ride in self._rides_by_id.items()
        }

    def restore(self, snapshot: dict[str, Any]) -> None:
        self._rides_by_id.clear()
        self._ride_ids_by_user_id.clear()

        for ride_id, raw in snapshot.items():
            ride = _ride_from_dict(raw)
            self._rides_by_id[ride_id] = ride
            self._ride_ids_by_user_id.setdefault(ride._user_id, []).append(
                ride._ride_id
            )


def _ride_to_dict(ride: Ride) -> dict[str, Any]:
    return {
        "user_id": ride.user_id,
        "vehicle_id": ride.vehicle_id,
        "start_time": ride.start_time.isoformat(),
        "end_time": ride.end_time.isoformat() if ride.end_time is not None else None,
        "start_latitude": ride.start_latitude,
        "start_longitude": ride.start_longitude,
        "end_latitude": ride.end_latitude,
        "end_longitude": ride.end_longitude,
        "distance": ride.distance,
        "fee": ride.fee,
        "status": ride.status().value,
        "ride_id": ride.ride_id,
    }


def _ride_from_dict(data: dict[str, Any]) -> Ride:
    user_id = str(data["user_id"])
    vehicle_id = str(data["vehicle_id"])
    ride_id = str(data["ride_id"])

    start_time_raw = str(data["start_time"])
    start_time = datetime.fromisoformat(start_time_raw)

    end_time: datetime | None
    end_time_raw = data.get("end_time")
    if isinstance(end_time_raw, str) and end_time_raw:
        end_time = datetime.fromisoformat(end_time_raw)
    else:
        end_time = None

    ride = Ride(
        user_id=user_id,
        vehicle_id=vehicle_id,
        start_time=start_time,
        end_time=end_time,
        start_latitude=float(data.get("start_latitude", 0.0)),
        start_longitude=float(data.get("start_longitude", 0.0)),
        end_latitude=float(data.get("end_latitude", 0.0)),
        end_longitude=float(data.get("end_longitude", 0.0)),
        distance=float(data.get("distance", 0.0)),
        fee=float(data.get("fee", 0.0)),
        ride_id=ride_id,
    )

    status_raw = str(data.get("status", RideStatus.ACTIVE.value))
    status = RideStatus(status_raw)

    if status == RideStatus.CANCELLED:
        if end_time is not None:
            raise ValueError("Invalid snapshot: cancelled ride cannot have end_time")
        ride.cancel()

    return ride
