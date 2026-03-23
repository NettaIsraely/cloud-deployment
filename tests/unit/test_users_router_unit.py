"""Unit tests for users_router: login, profile, payment update, upgrade, active users."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from tlvflow.api.app import app
from tlvflow.domain.users import ProUser
from tlvflow.persistence.active_users_repository import ActiveUsersRepository
from tlvflow.persistence.users_repository import UsersRepository


def _setup_state(client: TestClient) -> UsersRepository:
    repo = UsersRepository()
    client.app.state.users_repository = repo
    client.app.state.active_users_repository = ActiveUsersRepository()
    return repo


def _register_and_get_id(client: TestClient, email: str | None = None) -> str:
    email = email or f"u-{uuid4().hex[:8]}@test.com"
    resp = client.post(
        "/register",
        json={
            "name": "Test",
            "email": email,
            "password": "password123",
            "payment_method_id": "pm_1",
        },
    )
    assert resp.status_code == 201
    return resp.json()["user_id"]


# --- register: repo missing raises RuntimeError → 500 ---


def test_register_repo_missing() -> None:
    with TestClient(app, raise_server_exceptions=False) as client:
        client.app.state.users_repository = None
        resp = client.post(
            "/register",
            json={
                "name": "Test",
                "email": "test@test.com",
                "password": "password123",
                "payment_method_id": "pm_1",
            },
        )
    assert resp.status_code == 500


# --- register: generic ValueError → 400 ---


def test_register_short_password_returns_400() -> None:
    with TestClient(app) as client:
        _setup_state(client)
        resp = client.post(
            "/register",
            json={
                "name": "Test",
                "email": "valid@test.com",
                "password": "short",
                "payment_method_id": "pm_1",
            },
        )
    assert resp.status_code == 400


# --- login ---


def test_login_success() -> None:
    with TestClient(app) as client:
        _setup_state(client)
        user_id = _register_and_get_id(client, "login@test.com")
        resp = client.post(
            "/login", json={"email": "login@test.com", "password": "password123"}
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == user_id
    assert data["name"] == "Test"
    assert data["is_pro"] is False


def test_login_repo_missing_500() -> None:
    with TestClient(app) as client:
        client.app.state.users_repository = None
        resp = client.post(
            "/login", json={"email": "a@b.com", "password": "password123"}
        )
    assert resp.status_code == 500


def test_login_wrong_password_401() -> None:
    with TestClient(app) as client:
        _setup_state(client)
        _register_and_get_id(client, "login2@test.com")
        resp = client.post(
            "/login", json={"email": "login2@test.com", "password": "wrongpassword"}
        )
    assert resp.status_code == 401


def test_login_wrong_email_401() -> None:
    with TestClient(app) as client:
        _setup_state(client)
        resp = client.post(
            "/login", json={"email": "noone@test.com", "password": "password123"}
        )
    assert resp.status_code == 401


# --- profile /users/me ---


def test_profile_success() -> None:
    with TestClient(app) as client:
        _setup_state(client)
        user_id = _register_and_get_id(client, "me@test.com")
        resp = client.get("/users/me", params={"user_id": user_id})
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == user_id
    assert data["email"] == "me@test.com"


def test_profile_repo_missing_500() -> None:
    with TestClient(app) as client:
        client.app.state.users_repository = None
        resp = client.get("/users/me", params={"user_id": "u1"})
    assert resp.status_code == 500


def test_profile_user_not_found_404() -> None:
    with TestClient(app) as client:
        _setup_state(client)
        resp = client.get("/users/me", params={"user_id": "no-such-user"})
    assert resp.status_code == 404


# --- PATCH /users/{user_id}/payment-method ---


def test_patch_payment_method_success() -> None:
    with TestClient(app) as client:
        _setup_state(client)
        user_id = _register_and_get_id(client, "pay@test.com")
        resp = client.patch(
            f"/users/{user_id}/payment-method", json={"payment_method_id": "pm_new"}
        )
    assert resp.status_code == 200
    assert resp.json()["user_id"] == user_id


def test_patch_payment_method_repo_missing_500() -> None:
    with TestClient(app) as client:
        client.app.state.users_repository = None
        resp = client.patch(
            "/users/u1/payment-method", json={"payment_method_id": "pm_new"}
        )
    assert resp.status_code == 500


def test_patch_payment_method_user_not_found_404() -> None:
    with TestClient(app) as client:
        _setup_state(client)
        resp = client.patch(
            "/users/ghost/payment-method", json={"payment_method_id": "pm_new"}
        )
    assert resp.status_code == 404


# --- POST /user/upgrade ---


def test_upgrade_success() -> None:
    with TestClient(app) as client:
        _setup_state(client)
        user_id = _register_and_get_id(client, "upgrade@test.com")
        resp = client.post(
            "/user/upgrade",
            json={
                "user_id": user_id,
                "license_number": "LN123",
                "license_expiry": "2030-01-01T00:00:00Z",
            },
        )
    assert resp.status_code == 200
    assert resp.json()["user_id"] == user_id


def test_upgrade_repo_missing_500() -> None:
    with TestClient(app, raise_server_exceptions=False) as client:
        client.app.state.users_repository = None
        resp = client.post(
            "/user/upgrade",
            json={
                "user_id": "u1",
                "license_number": "LN123",
                "license_expiry": "2030-01-01",
            },
        )
    assert resp.status_code == 500


def test_upgrade_user_not_found_404() -> None:
    with TestClient(app) as client:
        _setup_state(client)
        resp = client.post(
            "/user/upgrade",
            json={
                "user_id": "nonexistent",
                "license_number": "LN123",
                "license_expiry": "2030-01-01",
            },
        )
    assert resp.status_code == 404


def test_upgrade_already_pro_409() -> None:
    with TestClient(app) as client:
        repo = _setup_state(client)
        pro = ProUser.register(
            name="Pro",
            email="pro@test.com",
            password="password123",
            payment_method_id="pm_1",
            user_id="pro1",
            license_number="LN_OLD",
            license_expiry=datetime(2030, 1, 1, tzinfo=UTC),
        )
        repo.add(pro)
        resp = client.post(
            "/user/upgrade",
            json={
                "user_id": "pro1",
                "license_number": "LN_NEW",
                "license_expiry": "2031-01-01",
            },
        )
    assert resp.status_code == 409


def test_upgrade_invalid_expiry_422() -> None:
    with TestClient(app) as client:
        _setup_state(client)
        user_id = _register_and_get_id(client, "bad_expiry@test.com")
        resp = client.post(
            "/user/upgrade",
            json={
                "user_id": user_id,
                "license_number": "LN123",
                "license_expiry": "not-a-date",
            },
        )
    assert resp.status_code == 422


def test_upgrade_with_image_url() -> None:
    with TestClient(app) as client:
        _setup_state(client)
        user_id = _register_and_get_id(client, "withimg@test.com")
        resp = client.post(
            "/user/upgrade",
            json={
                "user_id": user_id,
                "license_number": "LN789",
                "license_expiry": "2030-06-01",
                "license_image_url": "https://example.com/license.jpg",
            },
        )
    assert resp.status_code == 200


# --- /rides/active-users ---


def test_active_users_active_users_repo_missing_500() -> None:
    with TestClient(app) as client:
        _setup_state(client)
        client.app.state.active_users_repository = None
        resp = client.get("/rides/active-users")
    assert resp.status_code == 500


def test_active_users_users_repo_missing_500() -> None:
    with TestClient(app) as client:
        _setup_state(client)
        client.app.state.users_repository = None
        resp = client.get("/rides/active-users")
    assert resp.status_code == 500
