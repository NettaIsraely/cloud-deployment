from __future__ import annotations

from datetime import datetime
from typing import Any

from tlvflow.domain.users import ProUser, User


class UsersRepository:
    """In-memory repository for users, with snapshot/restore for persistence."""

    def __init__(self) -> None:
        self._users_by_id: dict[str, User] = {}
        self._user_id_by_email: dict[str, str] = {}

    def get_by_id(self, user_id: str) -> User | None:
        return self._users_by_id.get(user_id)

    def get_by_email(self, email: str) -> User | None:
        if not isinstance(email, str) or not email.strip():
            return None
        user_id = self._user_id_by_email.get(email.strip().lower())
        if user_id is None:
            return None
        return self._users_by_id.get(user_id)

    def add(self, user: User) -> None:
        self._users_by_id[user.user_id] = user
        self._user_id_by_email[user.email] = user.user_id

    def snapshot(self) -> dict[str, Any]:
        return {
            user_id: _user_to_dict(user) for user_id, user in self._users_by_id.items()
        }

    def restore(self, snapshot: dict[str, Any]) -> None:
        self._users_by_id.clear()
        self._user_id_by_email.clear()

        for user_id, raw in snapshot.items():
            user = _user_from_dict(raw)
            self._users_by_id[user_id] = user
            self._user_id_by_email[user.email] = user.user_id


def _user_to_dict(user: User) -> dict[str, Any]:
    base: dict[str, Any] = {
        "user_id": user.user_id,
        "name": user._name,
        "email": user.email,
        "password_hash": user._password_hash,
        "payment_method_id": user.payment_method_id,
    }

    if isinstance(user, ProUser):
        base["user_type"] = "pro"
        base["license_number"] = user._license_number
        base["license_expiry"] = user._license_expiry.isoformat()
        return base

    base["user_type"] = "user"
    return base


def _user_from_dict(data: dict[str, Any]) -> User:
    user_type = str(data.get("user_type", "user"))

    user_id = str(data["user_id"])
    name = str(data["name"])
    email = str(data["email"])
    password_hash = str(data["password_hash"])
    payment_method_id = str(data["payment_method_id"])

    if user_type == "pro":
        license_number = str(data["license_number"])
        license_expiry_raw = str(data["license_expiry"])
        license_expiry = datetime.fromisoformat(license_expiry_raw)
        return ProUser(
            user_id=user_id,
            name=name,
            email=email,
            password_hash=password_hash,
            payment_method_id=payment_method_id,
            license_number=license_number,
            license_expiry=license_expiry,
        )

    return User(
        user_id=user_id,
        name=name,
        email=email,
        password_hash=password_hash,
        payment_method_id=payment_method_id,
    )
