import base64
import hashlib
import hmac
import re
import secrets
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

if TYPE_CHECKING:
    from tlvflow.domain.vehicles import Vehicle

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class User:
    """Default user in the system.

    Users are split into regular and Pro accounts. Regular users can ride
    non-electric vehicles (bikes), while Pro users can ride any vehicle.
    """

    # Protected attributes
    _user_id: str
    _name: str
    _email: str
    _password_hash: str
    _payment_method_id: str

    # Ride tracking
    _ride_history: list[Any]
    _current_ride: Any | None
    _current_vehicle_id: str | None

    # Password hashing parameters
    _PWD_ALGO = "pbkdf2_sha256"
    _PWD_ITERATIONS = 210_000
    _SALT_BYTES = 16
    _DKLEN = 32

    def __init__(
        self,
        user_id: str,
        name: str,
        email: str,
        password_hash: str,
        payment_method_id: str,
    ) -> None:
        self._user_id = self._validate_user_id(user_id)
        self._name = self._validate_name(name)
        self._email = self._validate_email(email)
        self._password_hash = self._validate_password_hash(password_hash)
        self._payment_method_id = self._validate_payment_method_id(payment_method_id)

        self._ride_history = []
        self._current_ride = None
        self._current_vehicle_id = None

    # ----------------------------
    # Construction / authentication
    # ----------------------------
    @classmethod
    def register(
        cls,
        name: str,
        email: str,
        password: str,
        payment_method_id: str,
        *,
        user_id: str | None = None,
        license_number: str | None = None,
        license_expiry: datetime | None = None,
    ) -> "User":
        """Factory method used by the /register flow.

        Returns an instance with a generated user_id (uuid4 hex) unless provided.
        """
        uid = user_id or uuid4().hex
        pwd_hash = cls._hash_password(password)
        return cls(
            user_id=uid,
            name=name,
            email=email,
            password_hash=pwd_hash,
            payment_method_id=payment_method_id,
        )

    def login(self, password: str) -> bool:
        """Verify password against stored hash."""
        return self._verify_password(password, self._password_hash)

    # ----------------------------
    # Ride-related domain behavior
    # ----------------------------
    def start_ride(self, vehicle_id: str) -> None:
        """Mark that the user started a ride with the given vehicle.

        Enforces the rule: a user cannot be on more than one active ride.
        The service layer should attach the Ride object via set_current_ride()
        after creating it.
        """
        if self._current_ride is not None or self._current_vehicle_id is not None:
            raise ValueError("User already has an active ride")
        if not isinstance(vehicle_id, str) or not vehicle_id.strip():
            raise ValueError("vehicle_id must be a non-empty string")
        self._current_vehicle_id = vehicle_id.strip()

    def set_current_ride(self, ride: Any) -> None:
        """Attach the current ride object (called by service layer after start_ride)."""
        self._current_ride = ride

    def end_ride(self, station_id: str) -> None:
        """Finalize the current active ride and append it to history."""
        if self._current_ride is None and self._current_vehicle_id is None:
            raise ValueError("User has no active ride to end")
        if not isinstance(station_id, str) or not station_id.strip():
            raise ValueError("station_id must be a non-empty string")
        if self._current_ride is not None:
            self._ride_history.append(self._current_ride)
        self._current_ride = None
        self._current_vehicle_id = None

    def view_ride_history(self) -> tuple[Any, ...]:
        """Return an immutable snapshot of ride history."""
        return tuple(self._ride_history)

    def report_vehicle(
        self,
        *,
        vehicle_id: str,
        description: str,
    ) -> dict[str, str]:
        """Create a report payload for the given vehicle (diagram: report_vehicle)."""
        if not isinstance(vehicle_id, str) or not vehicle_id.strip():
            raise ValueError("vehicle_id must be a non-empty string")
        payload: dict[str, str] = {"vehicle_id": vehicle_id.strip()}
        if description:
            payload["description"] = description
        return payload

    def validate_license(self) -> bool:
        """
        Base users have no license requirement — always passes.
        ProUser overrides this with actual license validation.
        """
        return True

    def upgrade_to_pro(
        self, license_number: str, license_expiry: datetime
    ) -> "ProUser":
        """
        Create a ProUser with the same identity and credentials, plus license data.
        Preserves ride history and current ride state.
        """
        pro = ProUser(
            user_id=self._user_id,
            name=self._name,
            email=self._email,
            password_hash=self._password_hash,
            payment_method_id=self._payment_method_id,
            license_number=license_number,
            license_expiry=license_expiry,
        )
        pro._ride_history = list(self._ride_history)
        pro._current_ride = self._current_ride
        pro._current_vehicle_id = self._current_vehicle_id
        return pro

    # ----------------------------
    # Permissions
    # ----------------------------
    def can_rent(self, vehicle: "Vehicle") -> bool:
        """Regular default: only non-electric bikes."""
        return not vehicle.is_electric

    # ----------------------------
    # Read-only properties
    # ----------------------------
    @property
    def user_id(self) -> str:
        return self._user_id

    @property
    def email(self) -> str:
        return self._email

    @property
    def payment_method_id(self) -> str:
        return self._payment_method_id

    def update_payment_method(self, new_id: str) -> None:
        """Update the stored payment method id. Must be non-empty."""
        self._payment_method_id = self._validate_payment_method_id(new_id)

    @property
    def current_ride(self) -> Any | None:
        return self._current_ride

    # ----------------------------
    # Validation helpers
    # ----------------------------
    @staticmethod
    def _validate_user_id(user_id: str) -> str:
        if not isinstance(user_id, str) or not user_id.strip():
            raise ValueError("user_id must be a non-empty string")
        return user_id

    @staticmethod
    def _validate_name(name: str) -> str:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("name must be a non-empty string")
        return name.strip()

    @staticmethod
    def _validate_email(email: str) -> str:
        if not isinstance(email, str) or not _EMAIL_RE.match(email.strip()):
            raise ValueError("email must be a valid email address")
        return email.strip().lower()

    @staticmethod
    def _validate_payment_method_id(payment_method_id: str) -> str:
        if not isinstance(payment_method_id, str) or not payment_method_id.strip():
            raise ValueError("payment_method_id must be a non-empty string")
        return payment_method_id.strip()

    @classmethod
    def _validate_password_hash(cls, password_hash: str) -> str:
        if not isinstance(password_hash, str) or not password_hash.strip():
            raise ValueError("password_hash must be a non-empty string")
        # Accept only our own format: algo$iters$salt$hash
        parts = password_hash.split("$")
        if len(parts) != 4 or parts[0] != cls._PWD_ALGO:
            raise ValueError("password_hash has an invalid format")
        return password_hash

    # ----------------------------
    # Password hashing (stdlib)
    # ----------------------------
    @classmethod
    def _hash_password(cls, password: str) -> str:
        if not isinstance(password, str) or len(password) < 8:
            raise ValueError("password must be a string with at least 8 characters")

        salt = secrets.token_bytes(cls._SALT_BYTES)
        dk = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            cls._PWD_ITERATIONS,
            dklen=cls._DKLEN,
        )

        salt_b64 = base64.urlsafe_b64encode(salt).decode("ascii").rstrip("=")
        dk_b64 = base64.urlsafe_b64encode(dk).decode("ascii").rstrip("=")
        return f"{cls._PWD_ALGO}${cls._PWD_ITERATIONS}${salt_b64}${dk_b64}"

    @classmethod
    def _verify_password(cls, password: str, stored_hash: str) -> bool:
        try:
            algo, iters_s, salt_b64, dk_b64 = stored_hash.split("$", 3)
            if algo != cls._PWD_ALGO:
                return False
            iters = int(iters_s)
        except Exception:
            return False

        # Restore padding for base64 decode
        def _pad(s: str) -> str:
            return s + "=" * (-len(s) % 4)

        try:
            salt = base64.urlsafe_b64decode(_pad(salt_b64))
            expected = base64.urlsafe_b64decode(_pad(dk_b64))
        except Exception:
            return False

        dk = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            iters,
            dklen=len(expected),
        )
        return hmac.compare_digest(dk, expected)


class ProUser(User):
    """A user that can ride electric and non-electric vehicles (all vehicles)."""

    _license_number: str
    _license_expiry: datetime

    def __init__(
        self,
        user_id: str,
        name: str,
        email: str,
        password_hash: str,
        payment_method_id: str,
        *,
        license_number: str,
        license_expiry: datetime,
    ) -> None:
        super().__init__(
            user_id=user_id,
            name=name,
            email=email,
            password_hash=password_hash,
            payment_method_id=payment_method_id,
        )
        self._license_number = self._validate_license_number(license_number)
        self._license_expiry = self._validate_license_expiry(license_expiry)

    @classmethod
    def register(
        cls,
        name: str,
        email: str,
        password: str,
        payment_method_id: str,
        *,
        user_id: str | None = None,
        license_number: str | None = None,
        license_expiry: datetime | None = None,
    ) -> "ProUser":
        if not license_number:
            raise ValueError("license_number is required for ProUser")
        if license_expiry is None:
            raise ValueError("license_expiry is required for ProUser")
        uid = user_id or uuid4().hex
        pwd_hash = cls._hash_password(password)
        return cls(
            user_id=uid,
            name=name,
            email=email,
            password_hash=pwd_hash,
            payment_method_id=payment_method_id,
            license_number=license_number,
            license_expiry=license_expiry,
        )

    def validate_license(self, *, at: datetime | None = None) -> bool:
        """Return True if license is not expired at the given time (UTC)."""
        now = at or datetime.now(UTC)
        # Normalize naive datetimes as UTC
        if now.tzinfo is None:
            now = now.replace(tzinfo=UTC)
        exp = self._license_expiry
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=UTC)
        return exp >= now

    def can_rent(self, vehicle: "Vehicle") -> bool:
        """Pro users can rent any vehicle (license was verified at upgrade)."""
        return True

    @staticmethod
    def _validate_license_number(license_number: str) -> str:
        if not isinstance(license_number, str) or not license_number.strip():
            raise ValueError("license_number must be a non-empty string")
        return license_number.strip()

    @staticmethod
    def _validate_license_expiry(license_expiry: datetime) -> datetime:
        if not isinstance(license_expiry, datetime):
            raise ValueError("license_expiry must be a datetime")
        return license_expiry
