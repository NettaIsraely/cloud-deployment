"""Integration tests for the POST /register endpoint."""

from fastapi.testclient import TestClient

from tlvflow.api.app import app
from tlvflow.persistence.users_repository import UsersRepository

_VALID_PAYLOAD = {
    "name": "Alice",
    "email": "alice@example.com",
    "password": "securepass1",
    "payment_method_id": "pm_alice",
}


def test_register_success_returns_201_and_user_id() -> None:
    with TestClient(app) as client:
        client.app.state.users_repository = UsersRepository()

        resp = client.post("/register", json=_VALID_PAYLOAD)

    assert resp.status_code == 201
    data = resp.json()
    assert "user_id" in data
    assert isinstance(data["user_id"], str)
    assert data["user_id"] != ""


def test_register_duplicate_email_returns_409() -> None:
    with TestClient(app) as client:
        client.app.state.users_repository = UsersRepository()

        client.post("/register", json=_VALID_PAYLOAD)
        resp = client.post("/register", json=_VALID_PAYLOAD)

    assert resp.status_code == 409


def test_register_invalid_email_format_returns_422() -> None:
    payload = {**_VALID_PAYLOAD, "email": "not-an-email"}

    with TestClient(app) as client:
        client.app.state.users_repository = UsersRepository()

        resp = client.post("/register", json=payload)

    assert resp.status_code == 422


def test_register_missing_required_fields_returns_422() -> None:
    with TestClient(app) as client:
        client.app.state.users_repository = UsersRepository()

        resp = client.post("/register", json={})

    assert resp.status_code == 422
