from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from tlvflow.domain.enums import EventStatus, TreatmentType


class MaintenanceEvent:
    def __init__(
        self,
        vehicle_id: str,
        report_id: str,
        open_time: datetime,
        treatments: list[TreatmentType] | None = None,
    ):
        # Protected attributes
        self._event_id = uuid4().hex
        self._vehicle_id = vehicle_id
        self._report_id = report_id
        self._treatments: list[TreatmentType] = (
            treatments if treatments is not None else []
        )
        self._closed_time: datetime | None = None

        # Private attributes
        self.__open_time = open_time
        self.__status = EventStatus.OPEN

    def close_event(self) -> None:
        """
        Public method to close the maintenance event.
        """
        self.__status = EventStatus.CLOSED
        self._closed_time = datetime.now(UTC)
