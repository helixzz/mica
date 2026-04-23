# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnusedCallResult=false

from __future__ import annotations

import json
from typing import cast

import pytest
from fastapi import HTTPException, Request
from sqlalchemy import select

from app.models import AuditLog, Company, Department, SystemParameter, User, UserRole
from app.services.saml_config import get_saml_config
from app.services.saml_jit import upsert_saml_user


class _FakeRequest:
    def __init__(self, *, base_url: str = "http://testserver/") -> None:
        self.base_url = base_url
        self.url = type("Url", (), {"scheme": "http", "hostname": "testserver", "port": 80})()
        self.headers: dict[str, str] = {}


async def _get_user(db, username: str) -> User:
    return (await db.execute(select(User).where(User.username == username))).scalar_one()


async def _get_company(db, code: str) -> Company:
    return (await db.execute(select(Company).where(Company.code == code))).scalar_one()


async def _get_department(db, company_id, code: str) -> Department:
    return (
        await db.execute(
            select(Department).where(Department.company_id == company_id, Department.code == code)
        )
    ).scalar_one()


async def _set_param(db, key: str, value) -> None:
    row = (await db.execute(select(SystemParameter).where(SystemParameter.key == key))).scalar_one()
    row.value = value
    await db.flush()


@pytest.fixture(autouse=True)
def _clear_imported_service_cache():
    from app.services.system_params import system_params

    system_params.invalidate()
    yield
    system_params.invalidate()


async def _enable_saml(db) -> None:
    await _set_param(db, "auth.saml.enabled", True)
    await _set_param(db, "auth.saml.idp.entity_id", "https://adfs.example.com/adfs/services/trust")
    await _set_param(
        db,
        "auth.saml.idp.sso_url",
        "https://adfs.example.com/adfs/ls/",
    )
    await _set_param(db, "auth.saml.idp.x509_cert", "-----BEGIN CERTIFICATE-----ABC-----END CERTIFICATE-----")


async def test_get_saml_config_builds_runtime_defaults(seeded_db_session):
    await _enable_saml(seeded_db_session)

    config = await get_saml_config(seeded_db_session, cast(Request, cast(object, _FakeRequest())), "en-US")

    assert config.enabled is True
    assert config.sp_entity_id == "http://testserver/api/v1/saml/metadata"
    assert config.sp_acs_url == "http://testserver/api/v1/saml/acs"
    assert config.default_role == UserRole.REQUESTER.value
    assert config.idp_x509_cert == "ABC"


async def test_get_saml_config_rejects_invalid_group_mapping_json(seeded_db_session):
    await _enable_saml(seeded_db_session)
    await _set_param(seeded_db_session, "auth.saml.group_mapping", "not-json")

    with pytest.raises(HTTPException) as exc:
        await get_saml_config(seeded_db_session, cast(Request, cast(object, _FakeRequest())), "en-US")

    assert exc.value.status_code == 500
    assert exc.value.detail == "Configured SAML group mapping is invalid"


async def test_upsert_saml_user_creates_new_user_with_default_role(seeded_db_session):
    await _enable_saml(seeded_db_session)
    config = await get_saml_config(seeded_db_session, cast(Request, cast(object, _FakeRequest())), "en-US")

    user = await upsert_saml_user(
        seeded_db_session,
        config=config,
        external_id="ext-123",
        attributes={
            config.email_attribute: ["new.user@example.com"],
            config.display_name_attribute: ["New User"],
        },
        locale="en-US",
    )

    persisted = (
        await seeded_db_session.execute(select(User).where(User.email == "new.user@example.com"))
    ).scalar_one()
    audits = list(
        (
            await seeded_db_session.execute(
                select(AuditLog)
                .where(AuditLog.resource_id == str(user.id))
                .order_by(AuditLog.occurred_at)
            )
        ).scalars()
    )

    assert user.id == persisted.id
    assert user.auth_provider == "saml"
    assert user.sso_external_id == "ext-123"
    assert user.role == UserRole.REQUESTER.value
    assert user.password_hash is None
    assert user.username == "new_user"
    assert {audit.event_type for audit in audits} >= {"auth.sso.login", "auth.sso.provisioned"}


async def test_upsert_saml_user_is_idempotent_for_same_external_id(seeded_db_session):
    await _enable_saml(seeded_db_session)
    config = await get_saml_config(seeded_db_session, cast(Request, cast(object, _FakeRequest())), "en-US")
    first = await upsert_saml_user(
        seeded_db_session,
        config=config,
        external_id="ext-idempotent",
        attributes={config.email_attribute: ["repeat@example.com"]},
        locale="en-US",
    )
    first_login_at = first.last_login_at

    second = await upsert_saml_user(
        seeded_db_session,
        config=config,
        external_id="ext-idempotent",
        attributes={config.email_attribute: ["repeat@example.com"]},
        locale="en-US",
    )

    users = list(
        (await seeded_db_session.execute(select(User).where(User.email == "repeat@example.com"))).scalars()
    )
    assert len(users) == 1
    assert first.id == second.id
    assert second.last_login_at is not None
    assert first_login_at is not None
    assert second.last_login_at >= first_login_at


async def test_upsert_saml_user_links_existing_local_user_by_email(seeded_db_session):
    await _enable_saml(seeded_db_session)
    config = await get_saml_config(seeded_db_session, cast(Request, cast(object, _FakeRequest())), "en-US")
    alice = await _get_user(seeded_db_session, "alice")
    original_password_hash = alice.password_hash

    user = await upsert_saml_user(
        seeded_db_session,
        config=config,
        external_id="alice-sso",
        attributes={
            config.email_attribute: [alice.email],
            config.display_name_attribute: ["Alice SSO"],
        },
        locale="en-US",
    )

    refreshed = await _get_user(seeded_db_session, "alice")
    linked_audit = (
        await seeded_db_session.execute(
            select(AuditLog).where(AuditLog.resource_id == str(alice.id), AuditLog.event_type == "auth.sso.linked")
        )
    ).scalars().first()

    assert user.id == alice.id
    assert refreshed.password_hash == original_password_hash
    assert refreshed.auth_provider == "saml"
    assert refreshed.sso_external_id == "alice-sso"
    assert refreshed.display_name == "Alice SSO"
    assert linked_audit is not None


async def test_upsert_saml_user_applies_first_matching_group_mapping(seeded_db_session):
    await _enable_saml(seeded_db_session)
    demo_company = await _get_company(seeded_db_session, "DEMO")
    await _set_param(seeded_db_session, "auth.saml.group_mapping_enabled", True)
    await _set_param(
        seeded_db_session,
        "auth.saml.group_mapping",
        json.dumps(
            [
                {"group": "Finance", "role": UserRole.FINANCE_AUDITOR.value, "department_code": "FIN"},
                {"group": "IT", "role": UserRole.DEPT_MANAGER.value, "department_code": "IT"},
            ]
        ),
    )
    config = await get_saml_config(seeded_db_session, cast(Request, cast(object, _FakeRequest())), "en-US")

    user = await upsert_saml_user(
        seeded_db_session,
        config=config,
        external_id="grouped-user",
        attributes={
            config.email_attribute: ["grouped@example.com"],
            config.groups_attribute: ["Finance", "IT"],
        },
        locale="en-US",
    )
    finance_department = await _get_department(seeded_db_session, demo_company.id, "FIN")

    assert user.role == UserRole.FINANCE_AUDITOR.value
    assert user.department_id == finance_department.id


async def test_upsert_saml_user_falls_back_when_group_mapping_has_no_match(seeded_db_session):
    await _enable_saml(seeded_db_session)
    await _set_param(seeded_db_session, "auth.saml.group_mapping_enabled", True)
    await _set_param(
        seeded_db_session,
        "auth.saml.group_mapping",
        json.dumps([{"group": "Finance", "role": UserRole.FINANCE_AUDITOR.value}]),
    )
    config = await get_saml_config(seeded_db_session, cast(Request, cast(object, _FakeRequest())), "en-US")

    user = await upsert_saml_user(
        seeded_db_session,
        config=config,
        external_id="no-group-match",
        attributes={
            config.email_attribute: ["nomatch@example.com"],
            config.groups_attribute: ["Unknown"],
        },
        locale="en-US",
    )

    assert user.role == UserRole.REQUESTER.value


async def test_upsert_saml_user_rejects_when_jit_disabled_and_user_missing(seeded_db_session):
    await _enable_saml(seeded_db_session)
    await _set_param(seeded_db_session, "auth.saml.jit.enabled", False)
    config = await get_saml_config(seeded_db_session, cast(Request, cast(object, _FakeRequest())), "en-US")

    with pytest.raises(HTTPException) as exc:
        await upsert_saml_user(
            seeded_db_session,
            config=config,
            external_id="missing-jit-user",
            attributes={config.email_attribute: ["missing@example.com"]},
            locale="en-US",
        )

    assert exc.value.status_code == 403
    assert exc.value.detail == "No matching user was found and JIT provisioning is disabled"


async def test_upsert_saml_user_rejects_missing_email(seeded_db_session):
    await _enable_saml(seeded_db_session)
    config = await get_saml_config(seeded_db_session, cast(Request, cast(object, _FakeRequest())), "en-US")

    with pytest.raises(HTTPException) as exc:
        await upsert_saml_user(
            seeded_db_session,
            config=config,
            external_id="missing-email",
            attributes={config.groups_attribute: ["IT"]},
            locale="en-US",
        )

    assert exc.value.status_code == 400
    assert exc.value.detail == "SAML response is missing the email attribute"
