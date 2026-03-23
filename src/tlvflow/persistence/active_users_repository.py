from __future__ import annotations

from typing import Any


class ActiveUsersRepository:
    """In-memory repository tracking active users: user_id -> ride_id."""

    def __init__(self) -> None:
        self._ride_id_by_user_id: dict[str, str] = {}

    def get_ride_id(self, user_id: str) -> str | None:
        if not isinstance(user_id, str) or not user_id.strip():
            return None
        return self._ride_id_by_user_id.get(user_id.strip())

    def is_active(self, user_id: str) -> bool:
        return self.get_ride_id(user_id) is not None

    def set_active(self, user_id: str, ride_id: str) -> None:
        if not isinstance(user_id, str) or not user_id.strip():
            raise ValueError("user_id must be a non-empty string")
        if not isinstance(ride_id, str) or not ride_id.strip():
            raise ValueError("ride_id must be a non-empty string")
        self._ride_id_by_user_id[user_id.strip()] = ride_id.strip()

    def clear(self, user_id: str) -> None:
        if not isinstance(user_id, str) or not user_id.strip():
            return
        self._ride_id_by_user_id.pop(user_id.strip(), None)

    def get_active_user_ids(self) -> list[str]:
        return list(self._ride_id_by_user_id.keys())

    def snapshot(self) -> dict[str, Any]:
        return dict(self._ride_id_by_user_id)

    def restore(self, snapshot: dict[str, Any]) -> None:
        self._ride_id_by_user_id.clear()
        for user_id, ride_id in snapshot.items():
            self._ride_id_by_user_id[str(user_id)] = str(ride_id)
