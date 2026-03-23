from __future__ import annotations

from datetime import datetime
from typing import Any

from tlvflow.domain.enums import EventStatus, TreatmentType
from tlvflow.domain.maintenance_event import MaintenanceEvent


class MaintenanceRepository:
    """In-memory repository for maintenance events, with snapshot/restore for persistence."""

    def __init__(self) -> None:
        self._events_by_id: dict[str, MaintenanceEvent] = {}
        self._event_ids_by_vehicle_id: dict[str, list[str]] = {}

    def add(self, event: MaintenanceEvent) -> None:
        self._events_by_id[event._event_id] = event
        self._event_ids_by_vehicle_id.setdefault(event._vehicle_id, []).append(
            event._event_id
        )

    def get_by_id(self, event_id: str) -> MaintenanceEvent | None:
        return self._events_by_id.get(event_id)

    def get_all(self) -> list[MaintenanceEvent]:
        return list(self._events_by_id.values())

    def get_by_vehicle_id(self, vehicle_id: str) -> list[MaintenanceEvent]:
        event_ids = self._event_ids_by_vehicle_id.get(vehicle_id, [])
        return [
            self._events_by_id[eid] for eid in event_ids if eid in self._events_by_id
        ]

    def snapshot(self) -> dict[str, Any]:
        return {
            event_id: _event_to_dict(event)
            for event_id, event in self._events_by_id.items()
        }

    def restore(self, snapshot: dict[str, Any]) -> None:
        self._events_by_id.clear()
        self._event_ids_by_vehicle_id.clear()

        for event_id, raw in snapshot.items():
            event = _event_from_dict(raw)
            self._events_by_id[event_id] = event
            self._event_ids_by_vehicle_id.setdefault(event._vehicle_id, []).append(
                event._event_id
            )


def _event_to_dict(event: MaintenanceEvent) -> dict[str, Any]:
    return {
        "event_id": event._event_id,
        "vehicle_id": event._vehicle_id,
        "report_id": event._report_id,
        "treatments": [t.value for t in event._treatments],
        "open_time": event._MaintenanceEvent__open_time.isoformat(),  # type: ignore[attr-defined]
        "status": event._MaintenanceEvent__status.value,  # type: ignore[attr-defined]
        "closed_time": (
            event._closed_time.isoformat() if event._closed_time is not None else None
        ),
    }


def _event_from_dict(data: dict[str, Any]) -> MaintenanceEvent:
    open_time = datetime.fromisoformat(str(data["open_time"]))
    treatments = [TreatmentType(t) for t in data.get("treatments", [])]
    event = MaintenanceEvent(
        vehicle_id=str(data["vehicle_id"]),
        report_id=str(data["report_id"]),
        open_time=open_time,
        treatments=treatments,
    )
    event._event_id = str(data["event_id"])
    event._MaintenanceEvent__status = EventStatus(str(data["status"]))  # type: ignore[attr-defined]

    closed_time_raw = data.get("closed_time")
    if isinstance(closed_time_raw, str) and closed_time_raw:
        event._closed_time = datetime.fromisoformat(closed_time_raw)
    else:
        event._closed_time = None

    return event
