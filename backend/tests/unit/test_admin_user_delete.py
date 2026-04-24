from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.api.v1.admin import delete_user
from app.models import User, UserRole


async def _admin(db, username: str = "admin") -> User:
    return (await db.execute(select(User).where(User.username == username))).scalar_one()


async def _fresh_admin(db, username: str) -> User:
    from app.core.security import hash_password
    from app.db import new_uuid

    source = await _admin(db)
    u = User(
        id=new_uuid(),
        username=username,
        email=f"{username}@test.invalid",
        display_name=username,
        password_hash=hash_password("testpass123"),
        role=UserRole.ADMIN.value,
        company_id=source.company_id,
        department_id=source.department_id,
        preferred_locale="zh-CN",
        is_active=True,
    )
    db.add(u)
    await db.flush()
    return u


async def test_delete_user_rejects_self(seeded_db_session):
    actor = await _admin(seeded_db_session)
    with pytest.raises(HTTPException) as exc:
        await delete_user(actor.id, actor, seeded_db_session, None)
    assert exc.value.status_code == 409
    assert exc.value.detail == "user.cannot_delete_self"


async def test_delete_user_rejects_last_active_admin(seeded_db_session):
    actor = await _fresh_admin(seeded_db_session, "extra_admin_for_test")
    existing_admin = await _admin(seeded_db_session)
    existing_admin.is_active = False
    await seeded_db_session.flush()

    with pytest.raises(HTTPException) as exc:
        await delete_user(actor.id, actor, seeded_db_session, None)

    assert exc.value.status_code == 409
    assert exc.value.detail == "user.cannot_delete_self"


async def test_delete_user_rejects_user_with_references(seeded_db_session):
    from decimal import Decimal

    from app.db import new_uuid
    from app.models import PurchaseRequisition

    actor = await _admin(seeded_db_session)
    alice = (
        await seeded_db_session.execute(select(User).where(User.username == "alice"))
    ).scalar_one()

    pr = PurchaseRequisition(
        id=new_uuid(),
        pr_number=f"PR-REF-{uuid4().hex[:6]}",
        title="Alice PR",
        business_reason="alice owns this PR, so alice cannot be hard-deleted",
        status="draft",
        requester_id=alice.id,
        company_id=alice.company_id,
        department_id=alice.department_id,
        currency="CNY",
        total_amount=Decimal("100"),
    )
    seeded_db_session.add(pr)
    await seeded_db_session.flush()

    with pytest.raises(HTTPException) as exc:
        await delete_user(alice.id, actor, seeded_db_session, None)
    assert exc.value.status_code == 409
    assert exc.value.detail == "user.has_references"


async def test_delete_user_404_for_missing(seeded_db_session):
    actor = await _admin(seeded_db_session)
    with pytest.raises(HTTPException) as exc:
        await delete_user(uuid4(), actor, seeded_db_session, None)
    assert exc.value.status_code == 404


async def test_delete_user_succeeds_for_clean_user(seeded_db_session):
    from app.core.security import hash_password
    from app.db import new_uuid

    actor = await _admin(seeded_db_session)
    disposable = User(
        id=new_uuid(),
        username=f"disposable_{uuid4().hex[:8]}",
        email="disposable@test.invalid",
        display_name="Disposable",
        password_hash=hash_password("testpass123"),
        role=UserRole.REQUESTER.value,
        company_id=actor.company_id,
        department_id=actor.department_id,
        preferred_locale="zh-CN",
        is_active=True,
    )
    seeded_db_session.add(disposable)
    await seeded_db_session.flush()

    await delete_user(disposable.id, actor, seeded_db_session, None)

    remaining = (
        await seeded_db_session.execute(select(User).where(User.id == disposable.id))
    ).scalar_one_or_none()
    assert remaining is None
