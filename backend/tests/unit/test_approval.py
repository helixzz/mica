from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models import (
    ApprovalInstance,
    ApprovalTask,
    ApproverDelegation,
    User,
    UserRole,
)
from app.services import approval as svc


async def _user_by_role(db_session, role: UserRole) -> User:
    return (await db_session.execute(select(User).where(User.role == role))).scalars().first()


async def _alice(db_session) -> User:
    return (await db_session.execute(select(User).where(User.username == "alice"))).scalar_one()


async def test_small_amount_matches_single_stage_rule(seeded_db_session):
    alice = await _alice(seeded_db_session)
    instance = await svc.create_instance_for_pr(
        seeded_db_session,
        submitter=alice,
        biz_type="purchase_requisition",
        biz_id=uuid4(),
        biz_number="PR-TEST-0001",
        title="Small PR",
        amount=Decimal("5000"),
    )
    assert instance.total_stages == 1
    assert instance.current_stage == 1
    assert instance.status == "pending"
    assert instance.amount == Decimal("5000")

    tasks = (
        (
            await seeded_db_session.execute(
                select(ApprovalTask)
                .where(ApprovalTask.instance_id == instance.id)
                .order_by(ApprovalTask.stage_order)
            )
        )
        .scalars()
        .all()
    )
    assert len(tasks) == 1
    assert tasks[0].status == "pending"


async def test_large_amount_matches_two_stage_rule(seeded_db_session):
    alice = await _alice(seeded_db_session)
    instance = await svc.create_instance_for_pr(
        seeded_db_session,
        submitter=alice,
        biz_type="purchase_requisition",
        biz_id=uuid4(),
        biz_number="PR-TEST-0002",
        title="Large PR",
        amount=Decimal("150000"),
    )
    assert instance.total_stages == 2
    assert instance.current_stage == 1

    tasks = (
        (
            await seeded_db_session.execute(
                select(ApprovalTask)
                .where(ApprovalTask.instance_id == instance.id)
                .order_by(ApprovalTask.stage_order)
            )
        )
        .scalars()
        .all()
    )
    assert len(tasks) == 2
    assert tasks[0].status == "pending"
    assert tasks[1].status == "waiting"


async def test_boundary_amount_is_treated_as_large(seeded_db_session):
    alice = await _alice(seeded_db_session)
    instance = await svc.create_instance_for_pr(
        seeded_db_session,
        submitter=alice,
        biz_type="purchase_requisition",
        biz_id=uuid4(),
        biz_number="PR-TEST-BOUND",
        title="Boundary",
        amount=Decimal("100000"),
    )
    assert instance.total_stages == 2


async def test_approve_first_stage_advances_to_second(seeded_db_session):
    alice = await _alice(seeded_db_session)
    instance = await svc.create_instance_for_pr(
        seeded_db_session,
        submitter=alice,
        biz_type="purchase_requisition",
        biz_id=uuid4(),
        biz_number="PR-TEST-ADV",
        title="Advance",
        amount=Decimal("150000"),
    )

    bob = await _user_by_role(seeded_db_session, UserRole.DEPT_MANAGER)
    updated = await svc.act_on_task(seeded_db_session, bob, instance.id, "approve", "ok")
    assert updated.status == "pending"
    assert updated.current_stage == 2

    tasks = (
        (
            await seeded_db_session.execute(
                select(ApprovalTask)
                .where(ApprovalTask.instance_id == instance.id)
                .order_by(ApprovalTask.stage_order)
            )
        )
        .scalars()
        .all()
    )
    assert tasks[0].status == "approved"
    assert tasks[1].status == "pending"


async def test_approve_all_stages_marks_instance_approved(seeded_db_session):
    alice = await _alice(seeded_db_session)
    instance = await svc.create_instance_for_pr(
        seeded_db_session,
        submitter=alice,
        biz_type="purchase_requisition",
        biz_id=uuid4(),
        biz_number="PR-TEST-FULL",
        title="Full",
        amount=Decimal("5000"),
    )

    bob = await _user_by_role(seeded_db_session, UserRole.DEPT_MANAGER)
    final = await svc.act_on_task(seeded_db_session, bob, instance.id, "approve", "ok")
    assert final.status == "approved"
    assert final.completed_at is not None


async def test_reject_skips_remaining_waiting_tasks(seeded_db_session):
    alice = await _alice(seeded_db_session)
    instance = await svc.create_instance_for_pr(
        seeded_db_session,
        submitter=alice,
        biz_type="purchase_requisition",
        biz_id=uuid4(),
        biz_number="PR-TEST-REJ",
        title="Reject",
        amount=Decimal("150000"),
    )

    bob = await _user_by_role(seeded_db_session, UserRole.DEPT_MANAGER)
    rejected = await svc.act_on_task(seeded_db_session, bob, instance.id, "reject", "too expensive")
    assert rejected.status == "rejected"
    assert rejected.completed_at is not None

    tasks = (
        (
            await seeded_db_session.execute(
                select(ApprovalTask)
                .where(ApprovalTask.instance_id == instance.id)
                .order_by(ApprovalTask.stage_order)
            )
        )
        .scalars()
        .all()
    )
    assert tasks[0].status == "rejected"
    assert tasks[1].status == "skipped"


async def test_return_also_skips_waiting_tasks(seeded_db_session):
    alice = await _alice(seeded_db_session)
    instance = await svc.create_instance_for_pr(
        seeded_db_session,
        submitter=alice,
        biz_type="purchase_requisition",
        biz_id=uuid4(),
        biz_number="PR-TEST-RET",
        title="Return",
        amount=Decimal("150000"),
    )

    bob = await _user_by_role(seeded_db_session, UserRole.DEPT_MANAGER)
    returned = await svc.act_on_task(
        seeded_db_session, bob, instance.id, "return", "need more info"
    )
    assert returned.status == "returned"

    tasks = (
        (
            await seeded_db_session.execute(
                select(ApprovalTask)
                .where(ApprovalTask.instance_id == instance.id)
                .order_by(ApprovalTask.stage_order)
            )
        )
        .scalars()
        .all()
    )
    assert tasks[1].status == "skipped"


async def test_non_approver_cannot_act(seeded_db_session):
    from fastapi import HTTPException

    alice = await _alice(seeded_db_session)
    instance = await svc.create_instance_for_pr(
        seeded_db_session,
        submitter=alice,
        biz_type="purchase_requisition",
        biz_id=uuid4(),
        biz_number="PR-TEST-UNAUTH",
        title="Unauth",
        amount=Decimal("5000"),
    )

    with pytest.raises(HTTPException) as exc:
        await svc.act_on_task(seeded_db_session, alice, instance.id, "approve", "self-approve?")
    assert exc.value.status_code == 403


async def test_invalid_action_rejected(seeded_db_session):
    from fastapi import HTTPException

    alice = await _alice(seeded_db_session)
    instance = await svc.create_instance_for_pr(
        seeded_db_session,
        submitter=alice,
        biz_type="purchase_requisition",
        biz_id=uuid4(),
        biz_number="PR-TEST-BADACT",
        title="Bad",
        amount=Decimal("5000"),
    )
    bob = await _user_by_role(seeded_db_session, UserRole.DEPT_MANAGER)

    with pytest.raises(HTTPException) as exc:
        await svc.act_on_task(seeded_db_session, bob, instance.id, "reverse", None)
    assert exc.value.status_code == 422


async def test_delegation_forwards_to_delegate(seeded_db_session):
    from datetime import UTC, datetime, timedelta

    alice = await _alice(seeded_db_session)
    bob = await _user_by_role(seeded_db_session, UserRole.DEPT_MANAGER)
    dave = await _user_by_role(seeded_db_session, UserRole.PROCUREMENT_MGR)

    now = datetime.now(UTC)
    delegation = ApproverDelegation(
        from_user_id=bob.id,
        to_user_id=dave.id,
        starts_at=now - timedelta(days=1),
        ends_at=now + timedelta(days=7),
        reason="Business trip",
        is_active=True,
    )
    seeded_db_session.add(delegation)
    await seeded_db_session.flush()

    instance = await svc.create_instance_for_pr(
        seeded_db_session,
        submitter=alice,
        biz_type="purchase_requisition",
        biz_id=uuid4(),
        biz_number="PR-TEST-DELEG",
        title="Deleg",
        amount=Decimal("5000"),
    )

    tasks = (
        (
            await seeded_db_session.execute(
                select(ApprovalTask).where(ApprovalTask.instance_id == instance.id)
            )
        )
        .scalars()
        .all()
    )
    assigned = tasks[0].assignee_id
    assert assigned == dave.id


async def test_count_pending_for_user(seeded_db_session):
    alice = await _alice(seeded_db_session)
    bob = await _user_by_role(seeded_db_session, UserRole.DEPT_MANAGER)

    before = await svc.count_pending_for_user(seeded_db_session, bob.id)
    for i in range(2):
        await svc.create_instance_for_pr(
            seeded_db_session,
            submitter=alice,
            biz_type="purchase_requisition",
            biz_id=uuid4(),
            biz_number=f"PR-COUNT-{i}",
            title="count",
            amount=Decimal("1000"),
        )

    after = await svc.count_pending_for_user(seeded_db_session, bob.id)
    assert after >= before + 2


async def test_list_pending_tasks_for_user(seeded_db_session):
    alice = await _alice(seeded_db_session)
    bob = await _user_by_role(seeded_db_session, UserRole.DEPT_MANAGER)

    await svc.create_instance_for_pr(
        seeded_db_session,
        submitter=alice,
        biz_type="purchase_requisition",
        biz_id=uuid4(),
        biz_number="PR-LIST-0001",
        title="List",
        amount=Decimal("1000"),
    )
    tasks = await svc.list_pending_tasks_for_user(seeded_db_session, bob.id)
    assert len(tasks) >= 1
    assert all(t.status == "pending" for t in tasks)


async def test_get_instance_for_biz(seeded_db_session):
    alice = await _alice(seeded_db_session)
    biz_id = uuid4()
    created = await svc.create_instance_for_pr(
        seeded_db_session,
        submitter=alice,
        biz_type="purchase_requisition",
        biz_id=biz_id,
        biz_number="PR-GET-0001",
        title="Get",
        amount=Decimal("1000"),
    )

    fetched = await svc.get_instance_for_biz(seeded_db_session, "purchase_requisition", biz_id)
    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.biz_id == biz_id


async def test_get_instance_for_biz_missing_returns_none(seeded_db_session):
    fetched = await svc.get_instance_for_biz(seeded_db_session, "purchase_requisition", uuid4())
    assert fetched is None


async def test_no_matching_rule_falls_back_to_legacy_threshold(seeded_db_session):
    from sqlalchemy import delete

    await seeded_db_session.execute(
        delete(ApprovalInstance).where(ApprovalInstance.biz_type == "unknown_type")
    )

    alice = await _alice(seeded_db_session)
    instance = await svc.create_instance_for_pr(
        seeded_db_session,
        submitter=alice,
        biz_type="unknown_type",
        biz_id=uuid4(),
        biz_number="PR-LEGACY-0001",
        title="Legacy",
        amount=Decimal("5000"),
    )
    assert instance.total_stages == 1
    assert instance.current_stage == 1
