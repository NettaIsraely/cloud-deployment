"""Unit tests for users_service: login, register, upgrade, profile, payment, active users."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from tlvflow.domain.users import ProUser, User
from tlvflow.persistence.active_users_repository import ActiveUsersRepository
from tlvflow.persistence.users_repository import UsersRepository
from tlvflow.services.users_service import (
    get_active_users,
    get_profile,
    login_user,
    register_user,
    update_payment_method,
    upgrade_user_to_pro,
)


def _make_user(user_id: str = "u1", email: str = "u1@test.com") -> User:
    return User.register(
        name="Test User",
        email=email,
        password="password123",
        payment_method_id="pm_1",
        user_id=user_id,
    )


# --- login_user ---


def test_login_user_success() -> None:
    repo = UsersRepository()
    user = _make_user("u1", "login@test.com")
    repo.add(user)

    result = login_user(repo, email="login@test.com", password="password123")
    assert result["user_id"] == "u1"
    assert result["name"] == "Test User"
    assert result["is_pro"] is False


def test_login_user_wrong_email_raises() -> None:
    repo = UsersRepository()
    user = _make_user("u1", "login@test.com")
    repo.add(user)

    with pytest.raises(ValueError, match="Invalid email or password"):
        login_user(repo, email="wrong@test.com", password="password123")


def test_login_user_wrong_password_raises() -> None:
    repo = UsersRepository()
    user = _make_user("u1", "login@test.com")
    repo.add(user)

    with pytest.raises(ValueError, match="Invalid email or password"):
        login_user(repo, email="login@test.com", password="wrongpassword")


def test_login_pro_user_returns_is_pro_true() -> None:
    repo = UsersRepository()
    pro = ProUser.register(
        name="Pro",
        email="pro@test.com",
        password="password123",
        payment_method_id="pm_1",
        user_id="pro1",
        license_number="LN123",
        license_expiry=datetime(2030, 1, 1, tzinfo=UTC),
    )
    repo.add(pro)

    result = login_user(repo, email="pro@test.com", password="password123")
    assert result["is_pro"] is True


# --- register_user ---


async def test_register_user_success() -> None:
    repo = UsersRepository()
    uid = await register_user(
        repo,
        name="New User",
        email="new@test.com",
        password="password123",
        payment_method_id="pm_new",
    )
    assert uid
    assert repo.get_by_id(uid) is not None


async def test_register_user_duplicate_email_raises() -> None:
    repo = UsersRepository()
    await register_user(
        repo,
        name="First",
        email="dup@test.com",
        password="password123",
        payment_method_id="pm_1",
    )
    with pytest.raises(ValueError, match="email already registered"):
        await register_user(
            repo,
            name="Second",
            email="dup@test.com",
            password="password123",
            payment_method_id="pm_2",
        )


# --- upgrade_user_to_pro ---


async def test_upgrade_user_to_pro_success() -> None:
    repo = UsersRepository()
    user = _make_user("u_upgrade", "upgrade@test.com")
    repo.add(user)

    uid = await upgrade_user_to_pro(
        repo,
        user_id="u_upgrade",
        license_number="LN456",
        license_expiry=datetime(2030, 6, 1, tzinfo=UTC),
    )
    assert uid == "u_upgrade"
    assert isinstance(repo.get_by_id(uid), ProUser)


async def test_upgrade_user_to_pro_with_image_url() -> None:
    repo = UsersRepository()
    user = _make_user("u_img", "img@test.com")
    repo.add(user)

    uid = await upgrade_user_to_pro(
        repo,
        user_id="u_img",
        license_number="LN789",
        license_expiry=datetime(2030, 6, 1, tzinfo=UTC),
        license_image_url="https://example.com/license.jpg",
    )
    assert uid == "u_img"


async def test_upgrade_user_not_found_raises() -> None:
    repo = UsersRepository()
    with pytest.raises(ValueError, match="User not found"):
        await upgrade_user_to_pro(
            repo,
            user_id="nonexistent",
            license_number="LN123",
            license_expiry=datetime(2030, 1, 1, tzinfo=UTC),
        )


async def test_upgrade_already_pro_raises() -> None:
    repo = UsersRepository()
    pro = ProUser.register(
        name="Pro",
        email="pro2@test.com",
        password="password123",
        payment_method_id="pm_1",
        user_id="pro2",
        license_number="LN123",
        license_expiry=datetime(2030, 1, 1, tzinfo=UTC),
    )
    repo.add(pro)

    with pytest.raises(ValueError, match="User is already a Pro user"):
        await upgrade_user_to_pro(
            repo,
            user_id="pro2",
            license_number="LN456",
            license_expiry=datetime(2031, 1, 1, tzinfo=UTC),
        )


# --- get_profile ---


def test_get_profile_success() -> None:
    repo = UsersRepository()
    user = _make_user("u_profile", "profile@test.com")
    repo.add(user)

    profile = get_profile(repo, "u_profile")
    assert profile is not None
    assert profile["user_id"] == "u_profile"
    assert profile["email"] == "profile@test.com"
    assert profile["is_pro"] is False


def test_get_profile_not_found() -> None:
    repo = UsersRepository()
    assert get_profile(repo, "nonexistent") is None


# --- update_payment_method ---


def test_update_payment_method_success() -> None:
    repo = UsersRepository()
    user = _make_user("u_pay", "pay@test.com")
    repo.add(user)

    update_payment_method(repo, user_id="u_pay", payment_method_id="pm_new")
    updated = repo.get_by_id("u_pay")
    assert updated is not None
    assert updated.payment_method_id == "pm_new"


def test_update_payment_method_user_not_found_raises() -> None:
    repo = UsersRepository()
    with pytest.raises(ValueError, match="User not found"):
        update_payment_method(repo, user_id="missing", payment_method_id="pm_x")


# --- get_active_users ---


async def test_get_active_users_returns_active_users() -> None:
    users_repo = UsersRepository()
    active_repo = ActiveUsersRepository()

    user = _make_user("u_active", "active@test.com")
    users_repo.add(user)
    active_repo.set_active("u_active", "ride-1")

    result = await get_active_users(active_repo, users_repo)
    assert len(result) == 1
    assert result[0]["user_id"] == "u_active"


async def test_get_active_users_skips_missing_user() -> None:
    users_repo = UsersRepository()
    active_repo = ActiveUsersRepository()
    active_repo.set_active("ghost-user", "ride-1")

    result = await get_active_users(active_repo, users_repo)
    assert len(result) == 0


async def test_get_active_users_empty() -> None:
    users_repo = UsersRepository()
    active_repo = ActiveUsersRepository()

    result = await get_active_users(active_repo, users_repo)
    assert result == []
