from __future__ import annotations

from typing import assert_type

from tlvflow.domain.users import User
from tlvflow.persistence.users_repository import UsersRepository
from tlvflow.repositories.interfaces import UsersRepositoryProtocol


def test_users_repository_implements_protocol() -> None:
    repo: UsersRepositoryProtocol = UsersRepository()

    user = User.register(
        name="Test",
        email="test@example.com",
        password="password123",
        payment_method_id="pm_1",
    )
    repo.add(user)

    assert repo.get_by_id(user.user_id) is not None
    assert repo.get_by_email("test@example.com") is not None

    # Static type sanity (helps mypy, harmless for runtime).
    assert_type(repo, UsersRepositoryProtocol)
