# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models import (
    ApprovalInstance,
    Item,
    POStatus,
    PRStatus,
    PurchaseRequisition,
    Supplier,
    User,
    UserRole,
)
from app.schemas import PRCreateIn, PRItemIn, PRUpdateIn
from app.services import purchase as purchase_svc


async def _get_user(db, username: str = "alice") -> User:
    return (await db.execute(select(User).where(User.username == username))).scalar_one()


async def _get_item(db) -> Item:
    return (await db.execute(select(Item).where(Item.is_deleted.is_(False)).limit(1))).scalar_one()


async def _get_supplier(db, code: str = "SUP-DELL") -> Supplier:
    return (await db.execute(select(Supplier).where(Supplier.code == code))).scalar_one()


async def _create_buyer(db, username: str, company_id, department_id) -> User:
    buyer = User(
        username=username,
        email=f"{username}@test.local",
        display_name=f"{username.title()} Buyer",
        password_hash="test",
        role=UserRole.IT_BUYER.value,
        company_id=company_id,
        department_id=department_id,
        preferred_locale="zh-CN",
    )
    db.add(buyer)
    await db.flush()
    return buyer


def _pr_item(
    line_no: int,
    item_name: str,
    qty: str,
    unit_price: str,
    supplier_id=None,
    uom: str = "EA",
) -> PRItemIn:
    return PRItemIn(
        line_no=line_no,
        item_name=item_name,
        qty=Decimal(qty),
        unit_price=Decimal(unit_price),
        supplier_id=supplier_id,
        uom=uom,
    )


def _pr_payload(
    supplier_id,
    *,
    title: str = "Test PR",
    business_reason: str = "Testing",
    currency: str = "CNY",
    department_id=None,
    required_date: date | None = None,
    items: list[PRItemIn] | None = None,
) -> PRCreateIn:
    return PRCreateIn(
        title=title,
        business_reason=business_reason,
        currency=currency,
        department_id=department_id,
        required_date=required_date,
        items=items
        or [
            _pr_item(1, "Widget", "10", "100", supplier_id=supplier_id),
            _pr_item(2, "Cable", "5", "20", supplier_id=supplier_id),
        ],
    )


async def _create_pr(db, actor: User, supplier_id, **kwargs):
    return await purchase_svc.create_pr(db, actor, _pr_payload(supplier_id, **kwargs))


async def _mark_pr_approved(db, pr: PurchaseRequisition) -> None:
    pr.status = PRStatus.APPROVED.value
    await db.commit()


async def test_create_pr_creates_line_items_and_total(seeded_db_session):
    db = seeded_db_session
    actor = await _get_user(db, "alice")
    supplier = await _get_supplier(db)

    pr = await _create_pr(
        db,
        actor,
        supplier.id,
        required_date=date(2026, 5, 1),
    )

    assert pr.status == PRStatus.DRAFT.value
    assert pr.requester_id == actor.id
    assert pr.department_id == actor.department_id
    assert pr.required_date == date(2026, 5, 1)
    assert len(pr.items) == 2
    assert pr.items[0].amount == Decimal("1000.0000")
    assert pr.items[1].amount == Decimal("100.0000")
    assert pr.total_amount == Decimal("1100.0000")


async def test_create_pr_uses_explicit_department_when_provided(seeded_db_session):
    db = seeded_db_session
    actor = await _get_user(db, "dave")
    alice = await _get_user(db, "alice")
    supplier = await _get_supplier(db)

    pr = await _create_pr(db, actor, supplier.id, department_id=alice.department_id)

    assert pr.department_id == alice.department_id


async def test_create_pr_assigns_sequential_pr_numbers(seeded_db_session):
    db = seeded_db_session
    actor = await _get_user(db, "alice")
    supplier = await _get_supplier(db)
    year = datetime.now(UTC).year

    pr1 = await _create_pr(db, actor, supplier.id, title="PR 1")
    pr2 = await _create_pr(db, actor, supplier.id, title="PR 2")

    assert pr1.pr_number.startswith(f"PR-{year}-")
    assert pr2.pr_number.startswith(f"PR-{year}-")
    assert int(pr2.pr_number.split("-")[-1]) == int(pr1.pr_number.split("-")[-1]) + 1


async def test_update_pr_updates_fields_and_replaces_items(seeded_db_session):
    db = seeded_db_session
    actor = await _get_user(db, "alice")
    supplier = await _get_supplier(db)
    pr = await _create_pr(db, actor, supplier.id)
    old_item_ids = {item.id for item in pr.items}

    updated = await purchase_svc.update_pr(
        db,
        actor,
        pr.id,
        PRUpdateIn(
            title="Updated PR",
            business_reason="Updated reason",
            currency="USD",
            required_date=date(2026, 6, 1),
            items=[
                _pr_item(1, "Monitor", "3", "800", supplier_id=supplier.id),
                _pr_item(2, "Dock", "4", "250", supplier_id=supplier.id),
            ],
        ),
    )

    refreshed = (
        await db.execute(
            select(PurchaseRequisition)
            .where(PurchaseRequisition.id == pr.id)
            .options(selectinload(PurchaseRequisition.items))
            .execution_options(populate_existing=True)
        )
    ).scalar_one()

    assert updated.title == "Updated PR"
    assert refreshed.business_reason == "Updated reason"
    assert refreshed.currency == "USD"
    assert refreshed.required_date == date(2026, 6, 1)
    assert len(refreshed.items) == 2
    assert {item.id for item in refreshed.items}.isdisjoint(old_item_ids)
    assert refreshed.items[0].item_name == "Monitor"
    assert refreshed.items[1].item_name == "Dock"
    assert refreshed.total_amount == Decimal("3400.0000")


async def test_update_pr_allows_it_buyer_to_edit_approved_pr(seeded_db_session):
    db = seeded_db_session
    actor = await _get_user(db, "alice")
    supplier = await _get_supplier(db)
    pr = await _create_pr(db, actor, supplier.id)
    await _mark_pr_approved(db, pr)

    updated = await purchase_svc.update_pr(db, actor, pr.id, PRUpdateIn(title="Approved edit"))

    assert updated.status == PRStatus.APPROVED.value
    assert updated.title == "Approved edit"


async def test_update_pr_raises_not_found(seeded_db_session):
    db = seeded_db_session
    actor = await _get_user(db, "alice")

    with pytest.raises(HTTPException) as exc:
        await purchase_svc.update_pr(db, actor, uuid4(), PRUpdateIn(title="missing"))

    assert exc.value.status_code == 404
    assert exc.value.detail == "pr.not_found"


async def test_update_pr_forbids_unprivileged_non_owner(seeded_db_session):
    db = seeded_db_session
    owner = await _get_user(db, "alice")
    actor = await _get_user(db, "bob")
    supplier = await _get_supplier(db)
    pr = await _create_pr(db, owner, supplier.id)

    with pytest.raises(HTTPException) as exc:
        await purchase_svc.update_pr(db, actor, pr.id, PRUpdateIn(title="blocked"))

    assert exc.value.status_code == 403
    assert exc.value.detail == "insufficient_role"


async def test_update_pr_rejects_submitted_pr(seeded_db_session):
    db = seeded_db_session
    actor = await _get_user(db, "alice")
    supplier = await _get_supplier(db)
    pr = await _create_pr(db, actor, supplier.id)
    await purchase_svc.submit_pr(db, actor, pr.id)

    with pytest.raises(HTTPException) as exc:
        await purchase_svc.update_pr(db, actor, pr.id, PRUpdateIn(title="blocked"))

    assert exc.value.status_code == 409
    assert exc.value.detail == "pr.cannot_edit_submitted"


async def test_submit_pr_sets_status_and_creates_approval_instance(seeded_db_session):
    db = seeded_db_session
    actor = await _get_user(db, "alice")
    supplier = await _get_supplier(db)
    pr = await _create_pr(db, actor, supplier.id)

    submitted = await purchase_svc.submit_pr(db, actor, pr.id)

    instance = (
        await db.execute(
            select(ApprovalInstance).where(
                ApprovalInstance.biz_type == "purchase_requisition",
                ApprovalInstance.biz_id == pr.id,
            )
        )
    ).scalar_one()
    assert submitted.status == PRStatus.SUBMITTED.value
    assert submitted.submitted_at is not None
    assert instance.biz_number == pr.pr_number
    assert instance.amount == pr.total_amount
    assert instance.total_stages >= 1


async def test_submit_pr_raises_not_found(seeded_db_session):
    db = seeded_db_session
    actor = await _get_user(db, "alice")

    with pytest.raises(HTTPException) as exc:
        await purchase_svc.submit_pr(db, actor, uuid4())

    assert exc.value.status_code == 404
    assert exc.value.detail == "pr.not_found"


async def test_submit_pr_forbids_non_owner_non_admin(seeded_db_session):
    db = seeded_db_session
    owner = await _get_user(db, "alice")
    actor = await _get_user(db, "bob")
    supplier = await _get_supplier(db)
    pr = await _create_pr(db, owner, supplier.id)

    with pytest.raises(HTTPException) as exc:
        await purchase_svc.submit_pr(db, actor, pr.id)

    assert exc.value.status_code == 403
    assert exc.value.detail == "insufficient_role"


async def test_submit_pr_rejects_non_draft(seeded_db_session):
    db = seeded_db_session
    actor = await _get_user(db, "alice")
    supplier = await _get_supplier(db)
    pr = await _create_pr(db, actor, supplier.id)
    await purchase_svc.submit_pr(db, actor, pr.id)

    with pytest.raises(HTTPException) as exc:
        await purchase_svc.submit_pr(db, actor, pr.id)

    assert exc.value.status_code == 409
    assert exc.value.detail == "pr.cannot_submit_non_draft"


async def test_submit_pr_rejects_pr_without_items(seeded_db_session):
    db = seeded_db_session
    actor = await _get_user(db, "alice")
    pr = await purchase_svc.create_pr(
        db,
        actor,
        PRCreateIn(title="Empty PR", business_reason="Testing", currency="CNY", items=[]),
    )

    with pytest.raises(HTTPException) as exc:
        await purchase_svc.submit_pr(db, actor, pr.id)

    assert exc.value.status_code == 422
    assert exc.value.detail == "pr.no_items"


async def test_get_pr_returns_owner_record(seeded_db_session):
    db = seeded_db_session
    actor = await _get_user(db, "alice")
    supplier = await _get_supplier(db)
    created = await _create_pr(db, actor, supplier.id)

    pr = await purchase_svc.get_pr(db, actor, created.id)

    assert pr.id == created.id
    assert len(pr.items) == 2


async def test_get_pr_raises_not_found(seeded_db_session):
    db = seeded_db_session
    actor = await _get_user(db, "alice")

    with pytest.raises(HTTPException) as exc:
        await purchase_svc.get_pr(db, actor, uuid4())

    assert exc.value.status_code == 404
    assert exc.value.detail == "pr.not_found"


async def test_get_pr_forbids_other_buyer(seeded_db_session):
    db = seeded_db_session
    owner = await _get_user(db, "alice")
    other_buyer = await _create_buyer(db, "zoe", owner.company_id, owner.department_id)
    supplier = await _get_supplier(db)
    pr = await _create_pr(db, owner, supplier.id)

    with pytest.raises(HTTPException) as exc:
        await purchase_svc.get_pr(db, other_buyer, pr.id)

    assert exc.value.status_code == 403
    assert exc.value.detail == "insufficient_role"


async def test_get_pr_allows_department_manager_for_same_department(seeded_db_session):
    db = seeded_db_session
    owner = await _get_user(db, "alice")
    manager = await _get_user(db, "bob")
    supplier = await _get_supplier(db)
    pr = await _create_pr(db, owner, supplier.id)

    loaded = await purchase_svc.get_pr(db, manager, pr.id)

    assert loaded.id == pr.id


async def test_list_prs_for_buyer_returns_only_own_prs(seeded_db_session):
    db = seeded_db_session
    alice = await _get_user(db, "alice")
    dave = await _get_user(db, "dave")
    supplier = await _get_supplier(db)
    alice_pr = await _create_pr(db, alice, supplier.id, title="Alice PR")
    dave_pr = await _create_pr(db, dave, supplier.id, title="Dave PR")

    prs = await purchase_svc.list_prs_for_user(db, alice)
    pr_ids = [pr.id for pr in prs]

    assert alice_pr.id in pr_ids
    assert dave_pr.id not in pr_ids


async def test_list_prs_for_manager_filters_by_department(seeded_db_session):
    db = seeded_db_session
    alice = await _get_user(db, "alice")
    bob = await _get_user(db, "bob")
    dave = await _get_user(db, "dave")
    supplier = await _get_supplier(db)
    alice_pr = await _create_pr(db, alice, supplier.id, title="IT PR")
    dave_pr = await _create_pr(db, dave, supplier.id, title="Proc PR")

    prs = await purchase_svc.list_prs_for_user(db, bob)
    pr_ids = [pr.id for pr in prs]

    assert alice_pr.id in pr_ids
    assert dave_pr.id not in pr_ids


async def test_convert_pr_to_po_creates_order_from_approved_pr(seeded_db_session):
    db = seeded_db_session
    actor = await _get_user(db, "alice")
    supplier = await _get_supplier(db)
    pr = await _create_pr(db, actor, supplier.id)
    await _mark_pr_approved(db, pr)

    po = await purchase_svc.convert_pr_to_po(db, actor, pr.id)
    refreshed_pr = await purchase_svc.get_pr(db, actor, pr.id)

    assert po.pr_id == pr.id
    assert po.supplier_id == supplier.id
    assert po.status == POStatus.CONFIRMED.value
    assert po.total_amount == pr.total_amount
    assert len(po.items) == len(pr.items)
    assert po.items[0].item_name == pr.items[0].item_name
    assert po.items[1].amount == pr.items[1].amount
    assert refreshed_pr.status == PRStatus.CONVERTED.value


async def test_get_pr_downstream_returns_generated_po_and_primary_contract(seeded_db_session):
    from app.services import flow as flow_svc

    db = seeded_db_session
    actor = await _get_user(db, "alice")
    supplier = await _get_supplier(db)
    pr = await _create_pr(db, actor, supplier.id)
    await _mark_pr_approved(db, pr)
    po = await purchase_svc.convert_pr_to_po(db, actor, pr.id)
    contract = await flow_svc.create_contract(
        db, actor, po.id, title="Downstream link", total_amount=Decimal("100")
    )

    data = await purchase_svc.get_pr_downstream(db, actor, pr.id)

    po_ids = [p["id"] for p in data["purchase_orders"]]
    contract_ids = [c["id"] for c in data["contracts"]]
    assert str(po.id) in po_ids
    assert str(contract.id) in contract_ids
    assert data["contracts"][0]["po_id"] == str(po.id)


async def test_convert_pr_to_po_requires_approved_pr(seeded_db_session):
    db = seeded_db_session
    actor = await _get_user(db, "alice")
    supplier = await _get_supplier(db)
    pr = await _create_pr(db, actor, supplier.id)

    with pytest.raises(HTTPException) as exc:
        await purchase_svc.convert_pr_to_po(db, actor, pr.id)

    assert exc.value.status_code == 409
    assert exc.value.detail == "pr.must_be_approved_to_convert"


async def test_convert_pr_to_po_rejects_multiple_suppliers(seeded_db_session):
    db = seeded_db_session
    actor = await _get_user(db, "alice")
    supplier1 = await _get_supplier(db, "SUP-DELL")
    supplier2 = await _get_supplier(db, "SUP-LENOVO")
    pr = await purchase_svc.create_pr(
        db,
        actor,
        PRCreateIn(
            title="Mixed Supplier PR",
            business_reason="Testing",
            currency="CNY",
            items=[
                _pr_item(1, "Server", "1", "1000", supplier_id=supplier1.id),
                _pr_item(2, "Laptop", "1", "2000", supplier_id=supplier2.id),
            ],
        ),
    )
    await _mark_pr_approved(db, pr)

    with pytest.raises(HTTPException) as exc:
        await purchase_svc.convert_pr_to_po(db, actor, pr.id)

    assert exc.value.status_code == 422
    assert exc.value.detail == "pr.multiple_suppliers_not_supported_in_skeleton"


async def test_convert_pr_to_po_assigns_sequential_po_numbers(seeded_db_session):
    db = seeded_db_session
    actor = await _get_user(db, "alice")
    supplier = await _get_supplier(db)
    pr1 = await _create_pr(db, actor, supplier.id, title="Convert 1")
    pr2 = await _create_pr(db, actor, supplier.id, title="Convert 2")
    await _mark_pr_approved(db, pr1)
    await _mark_pr_approved(db, pr2)

    po1 = await purchase_svc.convert_pr_to_po(db, actor, pr1.id)
    po2 = await purchase_svc.convert_pr_to_po(db, actor, pr2.id)

    assert int(po2.po_number.split("-")[-1]) == int(po1.po_number.split("-")[-1]) + 1


async def test_convert_pr_to_po_auto_fills_sku_price_records(seeded_db_session):
    db = seeded_db_session
    actor = await _get_user(db, "alice")
    supplier = await _get_supplier(db)
    item = await _get_item(db)
    payload = PRCreateIn(
        title="SKU Auto-fill Test",
        business_reason="Testing",
        currency="CNY",
        items=[
            PRItemIn(
                line_no=1,
                item_id=item.id,
                item_name=item.name,
                qty=Decimal("5"),
                unit_price=Decimal("200"),
                supplier_id=supplier.id,
            )
        ],
    )
    pr = await purchase_svc.create_pr(db, actor, payload)
    await _mark_pr_approved(db, pr)

    po = await purchase_svc.convert_pr_to_po(db, actor, pr.id)

    from app.models import SKUPriceRecord

    records = (
        (
            await db.execute(
                select(SKUPriceRecord).where(
                    SKUPriceRecord.source_ref == po.po_number,
                    SKUPriceRecord.source_type == "actual_po",
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(records) == 1
    assert records[0].item_id == item.id
    assert records[0].supplier_id == supplier.id
    assert records[0].price == Decimal("200")
