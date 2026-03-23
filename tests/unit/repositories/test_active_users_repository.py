from __future__ import annotations

import pytest

from tlvflow.persistence.active_users_repository import ActiveUsersRepository


def test_set_and_get_and_is_active() -> None:
    repo = ActiveUsersRepository()

    assert repo.get_ride_id("u1") is None
    assert repo.is_active("u1") is False

    repo.set_active("u1", "r1")

    assert repo.get_ride_id("u1") == "r1"
    assert repo.is_active("u1") is True


def test_get_ride_id_invalid_inputs_return_none() -> None:
    repo = ActiveUsersRepository()

    assert repo.get_ride_id("") is None
    assert repo.get_ride_id("   ") is None

    # Runtime safety branch: method checks isinstance(user_id, str).
    assert repo.get_ride_id(None) is None  # type: ignore[arg-type]
    assert repo.get_ride_id(123) is None  # type: ignore[arg-type]


def test_set_active_rejects_invalid_inputs() -> None:
    repo = ActiveUsersRepository()

    with pytest.raises(ValueError):
        repo.set_active("", "r1")

    with pytest.raises(ValueError):
        repo.set_active("u1", "")

    with pytest.raises(ValueError):
        repo.set_active(None, "r1")  # type: ignore[arg-type]

    with pytest.raises(ValueError):
        repo.set_active("u1", None)  # type: ignore[arg-type]


def test_clear_is_idempotent_and_ignores_invalid_inputs() -> None:
    repo = ActiveUsersRepository()

    repo.set_active("u1", "r1")
    repo.clear("u1")
    repo.clear("u1")

    assert repo.get_ride_id("u1") is None

    repo.clear("")  # no-op
    repo.clear(None)  # type: ignore[arg-type]


def test_get_active_user_ids_returns_keys() -> None:
    repo = ActiveUsersRepository()

    repo.set_active("u1", "r1")
    repo.set_active("u2", "r2")

    assert set(repo.get_active_user_ids()) == {"u1", "u2"}


def test_snapshot_and_restore_round_trip() -> None:
    repo = ActiveUsersRepository()

    repo.set_active("u1", "r1")
    repo.set_active("u2", "r2")

    snapshot = repo.snapshot()

    restored = ActiveUsersRepository()
    restored.restore(snapshot)

    assert restored.get_ride_id("u1") == "r1"
    assert restored.get_ride_id("u2") == "r2"
    assert set(restored.get_active_user_ids()) == {"u1", "u2"}


def test_restore_clears_previous_state() -> None:
    repo = ActiveUsersRepository()

    repo.set_active("u1", "r1")
    repo.restore({"u2": "r2"})

    assert repo.get_ride_id("u1") is None
    assert repo.get_ride_id("u2") == "r2"


def test_restore_coerces_values_to_str() -> None:
    repo = ActiveUsersRepository()

    repo.restore({123: 456})

    assert repo.get_ride_id("123") == "456"
