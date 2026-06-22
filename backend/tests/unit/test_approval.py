from decimal import Decimal
from uuid import UUID, uuid4

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
    tasks = await svc.list_pending_tasks_for_user(seeded_db_session, bob)
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


async def test_list_pending_tasks_admin_sees_all(seeded_db_session):
    """Admin should see all pending tasks, not just their own."""
    alice = await _alice(seeded_db_session)
    bob = await _user_by_role(seeded_db_session, UserRole.DEPT_MANAGER)
    admin = await _user_by_role(seeded_db_session, UserRole.ADMIN)

    await svc.create_instance_for_pr(
        seeded_db_session,
        submitter=alice,
        biz_type="purchase_requisition",
        biz_id=uuid4(),
        biz_number="PR-ADMIN-VIEW-0001",
        title="Admin should see this",
        amount=Decimal("1000"),
    )

    bob_tasks = await svc.list_pending_tasks_for_user(seeded_db_session, bob)
    bob_count = len(bob_tasks)
    assert bob_count >= 1

    admin_tasks = await svc.list_pending_tasks_for_user(seeded_db_session, admin)
    assert len(admin_tasks) >= bob_count
    assignee_ids = {t.assignee_id for t in admin_tasks}
    assert bob.id in assignee_ids


async def test_proxy_routes_by_pr_department_not_actor(seeded_db_session):
    """v1.36.0: when admin/it_buyer/procurement_mgr submits on behalf of someone
    in a different department, approval routes to that target department's manager,
    not the actor's department.
    """
    from app.models import Department

    bob = await _user_by_role(seeded_db_session, UserRole.DEPT_MANAGER)
    procurement_mgr = await _user_by_role(seeded_db_session, UserRole.PROCUREMENT_MGR)

    fin_dept = (
        await seeded_db_session.execute(select(Department).where(Department.code == "FIN"))
    ).scalar_one()

    fin_manager = User(
        username="fin_dept_mgr",
        email="findeptmgr@example.com",
        display_name="Finance Dept Manager",
        password_hash="x",
        role=UserRole.DEPT_MANAGER.value,
        company_id=fin_dept.company_id,
        department_id=fin_dept.id,
        is_active=True,
    )
    seeded_db_session.add(fin_manager)
    await seeded_db_session.flush()

    instance = await svc.create_instance_for_pr(
        seeded_db_session,
        submitter=procurement_mgr,
        biz_type="purchase_requisition",
        biz_id=uuid4(),
        biz_number="PR-PROXY-DEPT-0001",
        title="proxy fin dept",
        amount=Decimal("5000"),
        department_id=fin_dept.id,
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
    assignee_ids = {t.assignee_id for t in tasks}
    assert fin_manager.id in assignee_ids
    assert bob.id not in assignee_ids


async def test_preferred_first_approver_is_honored_when_in_candidates(seeded_db_session):
    """If the submitter's preferred approver is in the rule-resolved candidate set,
    only that user gets the first-stage task.
    """
    alice = await _alice(seeded_db_session)
    bob = await _user_by_role(seeded_db_session, UserRole.DEPT_MANAGER)

    instance = await svc.create_instance_for_pr(
        seeded_db_session,
        submitter=alice,
        biz_type="purchase_requisition",
        biz_id=uuid4(),
        biz_number="PR-PREF-0001",
        title="pref ok",
        amount=Decimal("5000"),
        preferred_first_approver_id=bob.id,
    )

    first_stage_tasks = [
        t
        for t in (
            await seeded_db_session.execute(
                select(ApprovalTask).where(ApprovalTask.instance_id == instance.id)
            )
        )
        .scalars()
        .all()
        if t.stage_order == 1
    ]
    assert len(first_stage_tasks) == 1
    assert first_stage_tasks[0].assignee_id == bob.id
    assert first_stage_tasks[0].meta.get("preferred_by_submitter") is True


async def test_preferred_first_approver_rejected_when_not_in_candidates(seeded_db_session):
    """validate_preferred_approver_or_raise returns 422 with candidates list
    when the chosen user is not in the rule-resolved set.
    """
    from fastapi import HTTPException

    alice = await _alice(seeded_db_session)
    procurement_mgr = await _user_by_role(seeded_db_session, UserRole.PROCUREMENT_MGR)

    with pytest.raises(HTTPException) as exc:
        await svc.validate_preferred_approver_or_raise(
            seeded_db_session,
            submitter=alice,
            biz_type="purchase_requisition",
            amount=Decimal("5000"),
            preferred_first_approver_id=procurement_mgr.id,
            requester_id=alice.id,
            department_id=alice.department_id,
        )
    assert exc.value.status_code == 422
    detail = exc.value.detail
    assert isinstance(detail, dict)
    assert detail.get("error") == "approval.preferred_approver_not_in_candidates"
    candidate_ids = {c["user_id"] for c in detail.get("candidates", [])}
    assert procurement_mgr.id not in {UUID(cid) for cid in candidate_ids}


async def test_dept_manager_chain_lookup_walks_to_parent(seeded_db_session):
    """When a sub-team has no dept_manager, resolution walks up Department.parent_id
    until one is found.
    """
    from app.models import Department

    bob = await _user_by_role(seeded_db_session, UserRole.DEPT_MANAGER)

    it_dept = (
        await seeded_db_session.execute(select(Department).where(Department.code == "IT"))
    ).scalar_one()

    sub_dept = Department(
        company_id=it_dept.company_id,
        code="IT-AI",
        name_zh="AI 算法组",
        name_en="AI Team",
        parent_id=it_dept.id,
    )
    seeded_db_session.add(sub_dept)
    await seeded_db_session.flush()

    sub_member = User(
        username="ai_team_member",
        email="aiteam@example.com",
        display_name="AI Team Member",
        password_hash="x",
        role=UserRole.REQUESTER.value,
        company_id=sub_dept.company_id,
        department_id=sub_dept.id,
        is_active=True,
    )
    seeded_db_session.add(sub_member)
    await seeded_db_session.flush()

    instance = await svc.create_instance_for_pr(
        seeded_db_session,
        submitter=sub_member,
        biz_type="purchase_requisition",
        biz_id=uuid4(),
        biz_number="PR-CHAIN-0001",
        title="sub-team PR",
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
    assignee_ids = {t.assignee_id for t in tasks}
    assert bob.id in assignee_ids


async def test_preview_for_pr_returns_stage_chain(seeded_db_session):
    """preview_for_pr surfaces the stage chain + candidates without persisting anything."""
    alice = await _alice(seeded_db_session)
    bob = await _user_by_role(seeded_db_session, UserRole.DEPT_MANAGER)

    preview = await svc.preview_for_pr(
        seeded_db_session,
        submitter=alice,
        biz_type="purchase_requisition",
        amount=Decimal("150000"),
        requester_id=alice.id,
        department_id=alice.department_id,
    )

    assert preview["biz_type"] == "purchase_requisition"
    assert preview["is_legacy_fallback"] is False
    stages = preview["stages"]
    assert len(stages) == 2
    assert stages[0]["approver_role"] == UserRole.DEPT_MANAGER.value
    first_stage_user_ids = {c["user_id"] for c in stages[0]["candidates"]}
    assert bob.id in first_stage_user_ids


async def test_preview_for_pr_routes_by_target_department(seeded_db_session):
    """Preview reflects the target department, not the submitter's department."""
    from app.models import Department

    procurement_mgr = await _user_by_role(seeded_db_session, UserRole.PROCUREMENT_MGR)
    fin_dept = (
        await seeded_db_session.execute(select(Department).where(Department.code == "FIN"))
    ).scalar_one()

    fin_mgr = User(
        username="fin_mgr_for_preview",
        email="finmgrpv@example.com",
        display_name="Fin Manager",
        password_hash="x",
        role=UserRole.DEPT_MANAGER.value,
        company_id=fin_dept.company_id,
        department_id=fin_dept.id,
        is_active=True,
    )
    seeded_db_session.add(fin_mgr)
    await seeded_db_session.flush()

    preview = await svc.preview_for_pr(
        seeded_db_session,
        submitter=procurement_mgr,
        biz_type="purchase_requisition",
        amount=Decimal("5000"),
        department_id=fin_dept.id,
    )

    first_stage_ids = {c["user_id"] for c in preview["stages"][0]["candidates"]}
    assert fin_mgr.id in first_stage_ids
