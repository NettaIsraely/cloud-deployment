"""Integration tests for the GET /rides/active-users endpoint."""

from fastapi.testclient import TestClient

from tlvflow.api.app import app
from tlvflow.domain.users import User
from tlvflow.persistence.active_users_repository import ActiveUsersRepository
from tlvflow.persistence.users_repository import UsersRepository


def test_active_users_returns_correct_user_during_active_ride() -> None:
    user = User.register(
        name="Bob",
        email="bob@example.com",
        password="password123",
        payment_method_id="pm_bob",
    )

    users_repo = UsersRepository()
    users_repo.add(user)

    active_users_repo = ActiveUsersRepository()
    active_users_repo.set_active(user.user_id, "ride-1")

    with TestClient(app) as client:
        client.app.state.users_repository = users_repo
        client.app.state.active_users_repository = active_users_repo

        resp = client.get("/rides/active-users")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["users"]) == 1
    active = data["users"][0]
    assert active["user_id"] == user.user_id
    assert active["email"] == "bob@example.com"
    assert active["name"] == "Bob"
    assert active["payment_method_id"] == "pm_bob"


def test_active_users_returns_empty_list_when_no_active_rides() -> None:
    user = User.register(
        name="Carol",
        email="carol@example.com",
        password="password123",
        payment_method_id="pm_carol",
    )

    users_repo = UsersRepository()
    users_repo.add(user)

    with TestClient(app) as client:
        client.app.state.users_repository = users_repo
        client.app.state.active_users_repository = ActiveUsersRepository()

        resp = client.get("/rides/active-users")

    assert resp.status_code == 200
    assert resp.json()["users"] == []


def test_active_users_removes_user_after_ride_ends() -> None:
    user = User.register(
        name="Dan",
        email="dan@example.com",
        password="password123",
        payment_method_id="pm_dan",
    )

    users_repo = UsersRepository()
    users_repo.add(user)

    active_users_repo = ActiveUsersRepository()
    active_users_repo.set_active(user.user_id, "ride-2")

    with TestClient(app) as client:
        client.app.state.users_repository = users_repo
        client.app.state.active_users_repository = active_users_repo

        active_resp = client.get("/rides/active-users")
        assert len(active_resp.json()["users"]) == 1

        active_users_repo.clear(user.user_id)

        ended_resp = client.get("/rides/active-users")

    assert ended_resp.status_code == 200
    assert ended_resp.json()["users"] == []
