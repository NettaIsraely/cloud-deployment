from __future__ import annotations

from datetime import UTC, datetime

import pytest

from tlvflow.domain.users import ProUser, User
from tlvflow.persistence.users_repository import (
    UsersRepository,
    _user_from_dict,
    _user_to_dict,
)


def test_add_and_get_by_id_and_email() -> None:
    repo = UsersRepository()

    user = User.register(
        name=" Alice ",
        email="ALICE@Example.com ",
        password="password123",
        payment_method_id="pm_1",
    )

    repo.add(user)

    assert repo.get_by_id(user.user_id) is user
    assert repo.get_by_email("alice@example.com") is user
    assert repo.get_by_email("  ALICE@EXAMPLE.COM  ") is user


def test_get_by_email_invalid_inputs_return_none() -> None:
    repo = UsersRepository()

    assert repo.get_by_email("") is None
    assert repo.get_by_email("   ") is None

    # Runtime safety branch: method checks isinstance(email, str).
    assert repo.get_by_email(None) is None  # type: ignore[arg-type]
    assert repo.get_by_email(123) is None  # type: ignore[arg-type]


def test_snapshot_and_restore_round_trip_preserves_types_and_indexes() -> None:
    repo = UsersRepository()

    user = User.register(
        name="User",
        email="user@example.com",
        password="password123",
        payment_method_id="pm_u",
    )
    repo.add(user)

    expiry = datetime(2030, 1, 1, tzinfo=UTC)
    pro = ProUser.register(
        name="Pro",
        email="pro@example.com",
        password="password123",
        payment_method_id="pm_p",
        license_number="LIC-123",
        license_expiry=expiry,
    )
    repo.add(pro)

    snapshot = repo.snapshot()

    restored = UsersRepository()
    restored.restore(snapshot)

    u2 = restored.get_by_id(user.user_id)
    assert isinstance(u2, User)
    assert not isinstance(u2, ProUser)
    assert restored.get_by_email("user@example.com") is not None

    p2 = restored.get_by_id(pro.user_id)
    assert isinstance(p2, ProUser)
    assert p2 is not None
    assert p2._license_number == "LIC-123"
    assert p2._license_expiry == expiry
    assert restored.get_by_email("pro@example.com") is not None


def test_restore_clears_previous_state() -> None:
    repo = UsersRepository()

    u1 = User.register(
        name="U1",
        email="u1@example.com",
        password="password123",
        payment_method_id="pm_1",
    )
    repo.add(u1)

    u2 = User.register(
        name="U2",
        email="u2@example.com",
        password="password123",
        payment_method_id="pm_2",
    )

    repo.restore({u2.user_id: _user_to_dict(u2)})

    assert repo.get_by_id(u1.user_id) is None
    assert repo.get_by_email("u1@example.com") is None
    assert repo.get_by_id(u2.user_id) is not None
    assert repo.get_by_email("u2@example.com") is not None


def test_user_to_dict_branches_user_and_pro() -> None:
    base = User.register(
        name="Base",
        email="base@example.com",
        password="password123",
        payment_method_id="pm_b",
    )
    base_dict = _user_to_dict(base)
    assert base_dict["user_type"] == "user"

    expiry = datetime(2031, 5, 4, tzinfo=UTC)
    pro = ProUser.register(
        name="Pro",
        email="pro2@example.com",
        password="password123",
        payment_method_id="pm_p",
        license_number="LIC-999",
        license_expiry=expiry,
    )
    pro_dict = _user_to_dict(pro)
    assert pro_dict["user_type"] == "pro"
    assert pro_dict["license_number"] == "LIC-999"
    assert pro_dict["license_expiry"] == expiry.isoformat()


def test_user_from_dict_branches_user_pro_and_default_type() -> None:
    base = User.register(
        name="Base",
        email="base2@example.com",
        password="password123",
        payment_method_id="pm_b",
    )
    base_data = _user_to_dict(base)
    restored_base = _user_from_dict(base_data)
    assert isinstance(restored_base, User)
    assert not isinstance(restored_base, ProUser)

    expiry = datetime(2032, 2, 2, tzinfo=UTC)
    pro = ProUser.register(
        name="Pro",
        email="pro3@example.com",
        password="password123",
        payment_method_id="pm_p",
        license_number="LIC-321",
        license_expiry=expiry,
    )
    pro_data = _user_to_dict(pro)
    restored_pro = _user_from_dict(pro_data)
    assert isinstance(restored_pro, ProUser)
    assert restored_pro._license_number == "LIC-321"
    assert restored_pro._license_expiry == expiry

    # Default branch: unknown/missing user_type -> treat as base User.
    unknown_type = dict(base_data)
    unknown_type["user_type"] = "something-else"
    restored_unknown = _user_from_dict(unknown_type)
    assert isinstance(restored_unknown, User)
    assert not isinstance(restored_unknown, ProUser)


def test_user_from_dict_invalid_pro_license_expiry_raises() -> None:
    data = {
        "user_type": "pro",
        "user_id": "u123",
        "name": "BadPro",
        "email": "badpro@example.com",
        "password_hash": "pbkdf2_sha256$1$abc$def",
        "payment_method_id": "pm_x",
        "license_number": "LIC-0",
        "license_expiry": "not-an-iso-datetime",
    }

    with pytest.raises(ValueError):
        _user_from_dict(data)
