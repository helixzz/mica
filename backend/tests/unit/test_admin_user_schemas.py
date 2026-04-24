"""Regression tests for admin user CRUD schemas.

Prevents drift where UserCreateIn / UserUpdateIn omit valid UserRole values
(as happened with `requester` in v0.9.2 → v0.9.6, breaking local user
creation on production with a 422 '数据校验失败').
"""

import pytest
from pydantic import ValidationError

from app.api.v1.admin import UserCreateIn, UserUpdateIn
from app.models import UserRole


@pytest.mark.parametrize("role", [r.value for r in UserRole])
def test_user_create_accepts_every_valid_role(role):
    payload = UserCreateIn(
        username="alice",
        email="alice@example.com",
        display_name="Alice",
        password="supersecret",
        role=role,
        company_id="00000000-0000-0000-0000-000000000001",
    )
    assert payload.role == role


@pytest.mark.parametrize("role", [r.value for r in UserRole])
def test_user_update_accepts_every_valid_role(role):
    payload = UserUpdateIn(role=role)
    assert payload.role == role


def test_user_create_rejects_unknown_role():
    with pytest.raises(ValidationError):
        UserCreateIn(
            username="bob",
            email="bob@example.com",
            display_name="Bob",
            password="supersecret",
            role="godmode",
            company_id="00000000-0000-0000-0000-000000000001",
        )


def test_user_update_rejects_unknown_role():
    with pytest.raises(ValidationError):
        UserUpdateIn(role="godmode")
