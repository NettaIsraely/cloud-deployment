from __future__ import annotations

from datetime import datetime
from typing import Any

from tlvflow.domain.users import ProUser, User
from tlvflow.persistence.active_users_repository import ActiveUsersRepository
from tlvflow.persistence.users_repository import UsersRepository


def login_user(
    repo: UsersRepository,
    email: str,
    password: str,
) -> dict[str, Any]:
    """Authenticate by email and password. Returns user_id, name, is_pro. Raises ValueError on failure."""
    user = repo.get_by_email(email)
    if user is None:
        raise ValueError("Invalid email or password")
    if not user.login(password):
        raise ValueError("Invalid email or password")
    return {
        "user_id": user.user_id,
        "name": user._name,
        "is_pro": isinstance(user, ProUser),
    }


async def register_user(
    repo: UsersRepository,
    name: str,
    email: str,
    password: str,
    payment_method_id: str,
) -> str:
    if repo.get_by_email(email) is not None:
        raise ValueError("email already registered")
    user = User.register(
        name=name,
        email=email,
        password=password,
        payment_method_id=payment_method_id,
    )
    repo.add(user)
    return user.user_id


async def upgrade_user_to_pro(
    repo: UsersRepository,
    user_id: str,
    license_number: str,
    license_expiry: datetime,
    *,
    license_image_url: str | None = None,
) -> str:
    """Upgrade a regular user to Pro. Optionally pass license_image_url (picture of license)."""
    user = repo.get_by_id(user_id)
    if user is None:
        raise ValueError("User not found")
    if isinstance(user, ProUser):
        raise ValueError("User is already a Pro user")
    pro = user.upgrade_to_pro(
        license_number=license_number, license_expiry=license_expiry
    )
    repo.add(pro)
    if license_image_url:
        pass  # optional: store or validate image for audit
    return pro.user_id


async def get_active_users(
    active_users_repo: ActiveUsersRepository,
    users_repo: UsersRepository,
) -> list[dict[str, Any]]:
    result = []
    for user_id in active_users_repo.get_active_user_ids():
        user = users_repo.get_by_id(user_id)
        if user is not None:
            result.append(_user_to_dict(user))
    return result


def _user_to_dict(user: User) -> dict[str, Any]:
    return {
        "user_id": user.user_id,
        "name": user._name,
        "email": user.email,
        "payment_method_id": user.payment_method_id,
        "is_pro": isinstance(user, ProUser),
    }


def get_profile(repo: UsersRepository, user_id: str) -> dict[str, Any] | None:
    """Return non-sensitive profile for a user, or None if not found."""
    user = repo.get_by_id(user_id)
    if user is None:
        return None
    return _user_to_dict(user)


def update_payment_method(
    repo: UsersRepository,
    user_id: str,
    payment_method_id: str,
) -> None:
    """Update a user's payment method. Raises ValueError if user not found."""
    user = repo.get_by_id(user_id)
    if user is None:
        raise ValueError("User not found")
    user.update_payment_method(payment_method_id)
    repo.add(user)
