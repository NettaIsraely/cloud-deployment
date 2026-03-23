"""Unit tests for MaintenanceRepository."""

from datetime import UTC, datetime

from tlvflow.domain.enums import TreatmentType
from tlvflow.domain.maintenance_event import MaintenanceEvent
from tlvflow.persistence.maintenance_repository import MaintenanceRepository


def test_add_and_retrieve_by_id() -> None:
    repo = MaintenanceRepository()
    event = MaintenanceEvent(
        vehicle_id="v1", report_id="r1", open_time=datetime.now(UTC)
    )

    repo.add(event)

    assert repo.get_by_id(event._event_id) is event
    assert len(repo.get_all()) == 1


def test_get_by_vehicle_id_filters_correctly() -> None:
    repo = MaintenanceRepository()
    now = datetime.now(UTC)
    e1 = MaintenanceEvent(vehicle_id="v1", report_id="r1", open_time=now)
    e2 = MaintenanceEvent(vehicle_id="v2", report_id="r2", open_time=now)
    e3 = MaintenanceEvent(vehicle_id="v1", report_id="r3", open_time=now)

    repo.add(e1)
    repo.add(e2)
    repo.add(e3)

    v1_events = repo.get_by_vehicle_id("v1")
    assert len(v1_events) == 2
    assert e1 in v1_events
    assert e3 in v1_events

    v2_events = repo.get_by_vehicle_id("v2")
    assert len(v2_events) == 1
    assert e2 in v2_events


def test_snapshot_and_restore_round_trip() -> None:
    repo = MaintenanceRepository()
    now = datetime.now(UTC)

    treatments = [TreatmentType.CHAIN_LUBRICATION, TreatmentType.GENERAL_INSPECTION]
    open_event = MaintenanceEvent(
        vehicle_id="v1", report_id="r1", open_time=now, treatments=treatments
    )
    closed_event = MaintenanceEvent(vehicle_id="v1", report_id="r2", open_time=now)
    closed_event.close_event()

    repo.add(open_event)
    repo.add(closed_event)

    snapshot = repo.snapshot()

    new_repo = MaintenanceRepository()
    new_repo.restore(snapshot)

    restored_open = new_repo.get_by_id(open_event._event_id)
    restored_closed = new_repo.get_by_id(closed_event._event_id)

    assert restored_open is not None
    assert restored_open._event_id == open_event._event_id
    assert restored_open._vehicle_id == open_event._vehicle_id
    assert restored_open._report_id == open_event._report_id
    assert restored_open._closed_time is None
    assert restored_open._treatments == treatments

    assert restored_closed is not None
    assert restored_closed._event_id == closed_event._event_id
    assert restored_closed._closed_time is not None
    assert restored_closed._treatments == []

    assert len(new_repo.get_by_vehicle_id("v1")) == 2
