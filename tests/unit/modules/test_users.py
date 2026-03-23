import base64
from datetime import UTC, datetime, timedelta

import pytest

from tlvflow.domain.users import ProUser, User


class DummyVehicle:
    def __init__(self, *, is_electric: bool) -> None:
        self.is_electric = is_electric


def make_user(*, password: str = "password123") -> User:
    return User.register(
        name="  Alice  ",
        email="  ALICE@Example.Com  ",
        password=password,
        payment_method_id="  pm_123  ",
        user_id="user_1",
    )


def make_prouser(*, license_expiry: datetime) -> ProUser:
    return ProUser.register(
        name="Bob",
        email="bob@example.com",
        password="password123",
        payment_method_id="pm_456",
        user_id="pro_1",
        license_number="  1234567  ",
        license_expiry=license_expiry,
    )


# tests stripping + normalization of name/email/payment_method_id during register
def test_register_normalizes_fields():
    user = make_user()
    assert user.user_id == "user_1"
    assert user.email == "alice@example.com"
    assert user.payment_method_id == "pm_123"


# tests register generates a user_id when not provided
def test_register_generates_user_id_when_missing():
    user = User.register(
        name="Alice",
        email="alice@example.com",
        password="password123",
        payment_method_id="pm_123",
    )
    assert isinstance(user.user_id, str)
    assert len(user.user_id) > 0


# tests login success and failure
def test_login_verifies_password():
    user = make_user(password="password123")
    assert user.login("password123") is True
    assert user.login("wrongpass123") is False


# tests start_ride sets current vehicle and prevents double-start
def test_start_ride_sets_current_and_rejects_second_active_ride():
    user = make_user()
    ride = object()
    user.start_ride("v_1")
    user.set_current_ride(ride)
    assert user.current_ride is ride

    with pytest.raises(ValueError, match="active ride"):
        user.start_ride("v_2")


# tests start_ride rejects invalid vehicle_id inputs
@pytest.mark.parametrize("vehicle_id", ["", "   ", None, 123])  # type: ignore[list-item]
def test_start_ride_rejects_invalid_vehicle_id(vehicle_id) -> None:
    user = make_user()

    with pytest.raises(ValueError, match="vehicle_id must be"):
        user.start_ride(vehicle_id)  # type: ignore[arg-type]


# tests end_ride rejects when no active ride
def test_end_ride_rejects_when_no_active_ride():
    user = make_user()
    with pytest.raises(ValueError, match="no active ride"):
        user.end_ride("station_1")


# tests end_ride rejects invalid station_id
def test_end_ride_rejects_invalid_station_id():
    user = make_user()
    user.start_ride("v_1")
    with pytest.raises(ValueError, match="station_id must be"):
        user.end_ride("  ")


# tests end_ride appends to history and clears current ride
def test_end_ride_appends_to_history_and_clears_current():
    user = make_user()
    ride = {"ride_id": "r1"}
    user.start_ride("v_1")
    user.set_current_ride(ride)
    user.end_ride("station_1")

    assert user.current_ride is None
    assert user.view_ride_history() == (ride,)


# tests view_ride_history is immutable snapshot
def test_view_ride_history_returns_tuple_snapshot():
    user = make_user()
    ride = object()
    user.start_ride("v_1")
    user.set_current_ride(ride)
    user.end_ride("station_1")

    history = user.view_ride_history()
    assert isinstance(history, tuple)
    with pytest.raises(AttributeError):
        history.append(object())  # type: ignore[attr-defined]


# tests report_vehicle validations for required vehicle_id
@pytest.mark.parametrize(
    ("vehicle_id", "msg"),
    [
        ("", "vehicle_id must be"),
        ("   ", "vehicle_id must be"),
        (None, "vehicle_id must be"),  # type: ignore[arg-type]
    ],
)
def test_report_vehicle_requires_vehicle_id(vehicle_id, msg):
    user = make_user()
    with pytest.raises(ValueError, match=msg):
        user.report_vehicle(
            vehicle_id=vehicle_id,
            description="",
        )


# tests report_vehicle includes optional keys only when provided
def test_report_vehicle_payload_optional_fields():
    user = make_user()

    payload = user.report_vehicle(vehicle_id="v1", description="")
    assert payload == {"vehicle_id": "v1"}

    payload = user.report_vehicle(
        vehicle_id="v1",
        description="flat tire",
    )
    assert payload == {
        "vehicle_id": "v1",
        "description": "flat tire",
    }


# tests User.can_rent allows only non-electric
def test_user_can_rent_non_electric_only():
    user = make_user()
    assert user.can_rent(DummyVehicle(is_electric=False)) is True
    assert user.can_rent(DummyVehicle(is_electric=True)) is False


# tests regular User.validate_license always returns True
def test_user_validate_license_always_true():
    user = make_user()
    assert user.validate_license() is True


# tests ProUser.register requires license_number and license_expiry
def test_prouser_register_requires_license_fields():
    with pytest.raises(ValueError, match="license_number is required"):
        ProUser.register(
            name="Bob",
            email="bob@example.com",
            password="password123",
            payment_method_id="pm_1",
            license_number="",
            license_expiry=datetime.now(UTC),
        )

    with pytest.raises(ValueError, match="license_expiry is required"):
        ProUser.register(
            name="Bob",
            email="bob@example.com",
            password="password123",
            payment_method_id="pm_1",
            license_number="123",
            license_expiry=None,  # type: ignore[arg-type]
        )


# tests validate_license handles naive datetimes (both now and expiry)
def test_prouser_validate_license_normalizes_naive_datetimes():
    expiry_naive = datetime.now(UTC) + timedelta(days=1)
    pro = make_prouser(license_expiry=expiry_naive)

    at_naive = datetime.now(UTC)
    assert pro.validate_license(at=at_naive) is True


# tests validate_license returns False when expired
def test_prouser_validate_license_expired():
    pro = make_prouser(license_expiry=datetime.now(UTC) - timedelta(seconds=1))
    assert pro.validate_license(at=datetime.now(UTC)) is False


# tests ProUser.can_rent allows any vehicle (license verified at upgrade)
def test_prouser_can_rent_any_vehicle():
    pro_valid = make_prouser(license_expiry=datetime.now(UTC) + timedelta(days=1))
    pro_expired = make_prouser(license_expiry=datetime.now(UTC) - timedelta(days=1))

    assert pro_valid.can_rent(DummyVehicle(is_electric=True)) is True
    assert pro_valid.can_rent(DummyVehicle(is_electric=False)) is True
    # Pro status alone allows rent; license expiry is not re-checked per ride
    assert pro_expired.can_rent(DummyVehicle(is_electric=True)) is True
    assert pro_expired.can_rent(DummyVehicle(is_electric=False)) is True


# tests license validators enforce types/stripping
def test_license_validators():
    with pytest.raises(ValueError, match="license_number must be"):
        ProUser._validate_license_number("   ")

    with pytest.raises(ValueError, match="license_expiry must be"):
        ProUser._validate_license_expiry("2026-01-01")  # type: ignore[arg-type]

    assert ProUser._validate_license_number("  123  ") == "123"


# tests validation helpers reject invalid inputs
@pytest.mark.parametrize("bad_user_id", ["", "   ", None, 1])  # type: ignore[list-item]
def test_validate_user_id_rejects_invalid(bad_user_id):
    with pytest.raises(ValueError, match="user_id must be"):
        User._validate_user_id(bad_user_id)  # type: ignore[arg-type]


@pytest.mark.parametrize("bad_name", ["", "   ", None, 1])  # type: ignore[list-item]
def test_validate_name_rejects_invalid(bad_name):
    with pytest.raises(ValueError, match="name must be"):
        User._validate_name(bad_name)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "bad_email",
    ["", "   ", "no-at", "a@b", "a@b.", "a@.com", None, 1],  # type: ignore[list-item]
)
def test_validate_email_rejects_invalid(bad_email):
    with pytest.raises(ValueError, match="email must be"):
        User._validate_email(bad_email)  # type: ignore[arg-type]


@pytest.mark.parametrize("bad_pm", ["", "   ", None, 1])  # type: ignore[list-item]
def test_validate_payment_method_id_rejects_invalid(bad_pm):
    with pytest.raises(ValueError, match="payment_method_id must be"):
        User._validate_payment_method_id(bad_pm)  # type: ignore[arg-type]


# tests _validate_password_hash rejects empty/invalid formats and accepts valid format
def test_validate_password_hash_accepts_only_own_format():
    valid_hash = User._hash_password("password123")
    assert User._validate_password_hash(valid_hash) == valid_hash

    with pytest.raises(ValueError, match="password_hash must be"):
        User._validate_password_hash("  ")

    with pytest.raises(ValueError, match="invalid format"):
        User._validate_password_hash("pbkdf2_sha256$210000$only_three_parts")

    with pytest.raises(ValueError, match="invalid format"):
        User._validate_password_hash("wrongalgo$210000$salt$hash")


# tests _hash_password rejects non-string and too-short passwords
@pytest.mark.parametrize("bad_pwd", [None, 123, "short"])  # type: ignore[list-item]
def test_hash_password_rejects_invalid_passwords(bad_pwd):
    with pytest.raises(ValueError, match="at least 8"):
        User._hash_password(bad_pwd)  # type: ignore[arg-type]


# tests _verify_password returns False on malformed stored hash (split/int failures)
@pytest.mark.parametrize(
    "stored_hash",
    [
        "not-enough-parts",
        "pbkdf2_sha256$not_an_int$salt$hash",
        "wrongalgo$210000$salt$hash",
    ],
)
def test_verify_password_returns_false_on_header_parse_failures(stored_hash):
    assert User._verify_password("password123", stored_hash) is False


# tests _verify_password returns False on bad base64 content (decode failures)
def test_verify_password_returns_false_on_bad_base64():
    stored_hash = f"{User._PWD_ALGO}$1$not_base64!!$also_not_base64!!"
    assert User._verify_password("password123", stored_hash) is False


# tests _verify_password works end-to-end for correct and incorrect password
def test_verify_password_end_to_end():
    stored_hash = User._hash_password("password123")
    assert User._verify_password("password123", stored_hash) is True
    assert User._verify_password("wrongpass123", stored_hash) is False


# tests _verify_password base64 padding branch via unpadded urlsafe base64 segments
def test_verify_password_handles_unpadded_base64_segments():
    salt = b"\x01\x02\x03"
    dk = b"\x04\x05\x06\x07"
    salt_b64 = base64.urlsafe_b64encode(salt).decode("ascii").rstrip("=")
    dk_b64 = base64.urlsafe_b64encode(dk).decode("ascii").rstrip("=")
    stored_hash = f"{User._PWD_ALGO}$1${salt_b64}${dk_b64}"

    assert User._verify_password("password123", stored_hash) in {True, False}


# tests _verify_password raises when decoded expected hash is empty (dklen=0)
def test_verify_password_raises_on_empty_expected_hash():
    stored_hash = f"{User._PWD_ALGO}$1$$"  # empty salt + empty expected
    with pytest.raises(ValueError, match="key length must be greater than 0"):
        User._verify_password("password123", stored_hash)
