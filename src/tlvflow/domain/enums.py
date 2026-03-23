from enum import Enum


class VehicleStatus(Enum):
    """Enumeration for vehicle status."""

    AVAILABLE = "available"
    IN_USE = "in_use"
    AWAITING_REPORT_REVIEW = "awaiting_report_review"
    DEGRADED = "degraded"


class ReportStatus(Enum):
    """Enumeration for vehicle report status."""

    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    VERIFIED = "verified"
    REJECTED = "rejected"


class RideStatus(Enum):
    """Enumeration for ride status."""

    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class EventStatus(Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"


class PaymentKind(Enum):
    """Type of payment record."""

    CHARGE = "charge"
    RECEIPT = "receipt"
    REFUND = "refund"


class TreatmentType(Enum):
    """Types of maintenance treatments that can be applied to vehicles."""

    GENERAL_INSPECTION = "general_inspection"
    CHAIN_LUBRICATION = "chain_lubrication"
    BATTERY_INSPECTION = "battery_inspection"
    SCOOTER_FIRMWARE_UPDATE = "scooter_firmware_update"
