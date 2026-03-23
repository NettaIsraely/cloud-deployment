from datetime import datetime

import pytest

from tlvflow.domain.enums import ReportStatus
from tlvflow.domain.reports import VehicleReport


@pytest.fixture
def base_submission_time():
    return datetime(2026, 3, 2, 12, 0, 0)


@pytest.fixture
def valid_report(base_submission_time):
    """Fixture to provide a standard, valid VehicleReport instance."""
    return VehicleReport(
        user_id="user_123",
        vehicle_id="veh_456",
        submission_time=base_submission_time,
        image_url="https://example.com/damage_photo.jpg",
        description="Scratch on the left door.",
    )


def test_vehicle_report_initialization(base_submission_time):
    """Test that a new report initializes with correct attributes."""
    report = VehicleReport(
        user_id="user_123",
        vehicle_id="veh_456",
        submission_time=base_submission_time,
        image_url="https://example.com/damage.png",
        description="Dent on bumper",
    )

    # Check protected attributes
    assert report._user_id == "user_123"
    assert report._vehicle_id == "veh_456"
    assert isinstance(report._report_id, str)
    assert len(report._report_id) == 32

    # Check private attributes using name mangling
    assert report._VehicleReport__submission_time == base_submission_time
    assert report._VehicleReport__image_url == "https://example.com/damage.png"
    assert report._VehicleReport__description == "Dent on bumper"
    assert report._VehicleReport__status == ReportStatus.SUBMITTED


@pytest.mark.parametrize(
    "valid_url",
    [
        "http://example.com/image.png",
        "https://example.com/image.jpg",
        "https://example.com/image.JPEG",
        "http://domain.org/path/to/img.gif",
        "https://site.net/pic.bmp",
    ],
)
def test_verify_damage_success(valid_report, valid_url):
    """Test verify_damage returns True and updates status."""
    valid_report._VehicleReport__image_url = valid_url

    result = valid_report.verify_damage()

    assert result is True
    assert valid_report._VehicleReport__status == ReportStatus.VERIFIED


@pytest.mark.parametrize(
    "invalid_url",
    [
        "ftp://example.com/image.jpg",
        "https://example.com/image.pdf",
        "https://example.com/image",
        "just_a_string",
        "http://example.com/image.jpg.exe",
    ],
)
def test_verify_damage_rejection(valid_report, invalid_url):
    """Test verify_damage returns False and updates status to REJECTED."""
    valid_report._VehicleReport__image_url = invalid_url

    result = valid_report.verify_damage()

    assert result is False
    assert valid_report._VehicleReport__status == ReportStatus.REJECTED


def test_submit_report(valid_report):
    """Test that submit_report resets the status back to SUBMITTED."""
    valid_report._VehicleReport__status = ReportStatus.REJECTED
    valid_report.submit_report()

    assert valid_report._VehicleReport__status == ReportStatus.SUBMITTED
