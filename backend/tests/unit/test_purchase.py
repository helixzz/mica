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
    Company,
    CostCenter,
    Department,
    Item,
    POStatus,
    PRStatus,
    PurchaseRequisition,
    Supplier,
    User,
    UserRole,
    user_cost_centers,
    user_departments,
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

    pos = await purchase_svc.convert_pr_to_po(db, actor, pr.id)
    refreshed_pr = await purchase_svc.get_pr(db, actor, pr.id)

    assert len(pos) == 1
    po = pos[0]
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
    pos = await purchase_svc.convert_pr_to_po(db, actor, pr.id)
    po = pos[0]
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


async def test_convert_pr_to_po_splits_by_supplier_atomically(seeded_db_session):
    db = seeded_db_session
    actor = await _get_user(db, "alice")
    supplier1 = await _get_supplier(db, "SUP-DELL")
    supplier2 = await _get_supplier(db, "SUP-LENOVO")
    pr = await purchase_svc.create_pr(
        db,
        actor,
        PRCreateIn(
            title="Mixed Supplier PR",
            business_reason="Testing multi-supplier split",
            currency="CNY",
            items=[
                _pr_item(1, "Server", "1", "1000", supplier_id=supplier1.id),
                _pr_item(2, "Server-2", "2", "1500", supplier_id=supplier1.id),
                _pr_item(3, "Laptop", "1", "2000", supplier_id=supplier2.id),
            ],
        ),
    )
    await _mark_pr_approved(db, pr)

    pos = await purchase_svc.convert_pr_to_po(db, actor, pr.id)
    refreshed_pr = await purchase_svc.get_pr(db, actor, pr.id)

    assert len(pos) == 2
    by_supplier = {p.supplier_id: p for p in pos}
    assert set(by_supplier.keys()) == {supplier1.id, supplier2.id}
    po1 = by_supplier[supplier1.id]
    po2 = by_supplier[supplier2.id]
    assert len(po1.items) == 2
    assert len(po2.items) == 1
    assert po1.total_amount == Decimal("1000") + Decimal("3000")
    assert po2.total_amount == Decimal("2000")
    assert po1.po_number != po2.po_number
    assert refreshed_pr.status == PRStatus.CONVERTED.value


async def test_convert_pr_to_po_three_suppliers_split(seeded_db_session):
    db = seeded_db_session
    actor = await _get_user(db, "alice")
    s1 = await _get_supplier(db, "SUP-DELL")
    s2 = await _get_supplier(db, "SUP-LENOVO")
    s3 = await _get_supplier(db, "SUP-APPLE")
    pr = await purchase_svc.create_pr(
        db,
        actor,
        PRCreateIn(
            title="Three-way",
            business_reason="Testing",
            currency="CNY",
            items=[
                _pr_item(1, "A", "1", "100", supplier_id=s1.id),
                _pr_item(2, "B", "1", "200", supplier_id=s2.id),
                _pr_item(3, "C", "1", "300", supplier_id=s3.id),
            ],
        ),
    )
    await _mark_pr_approved(db, pr)

    pos = await purchase_svc.convert_pr_to_po(db, actor, pr.id)

    assert len(pos) == 3
    assert {p.supplier_id for p in pos} == {s1.id, s2.id, s3.id}
    assert sum(p.total_amount for p in pos) == Decimal("600")


async def test_convert_pr_to_po_rejects_items_missing_supplier(seeded_db_session):
    db = seeded_db_session
    actor = await _get_user(db, "alice")
    supplier = await _get_supplier(db, "SUP-DELL")
    pr = await purchase_svc.create_pr(
        db,
        actor,
        PRCreateIn(
            title="Incomplete supplier PR",
            business_reason="Testing",
            currency="CNY",
            items=[
                _pr_item(1, "Has supplier", "1", "1000", supplier_id=supplier.id),
                _pr_item(2, "No supplier", "1", "500", supplier_id=None),
            ],
        ),
    )
    await _mark_pr_approved(db, pr)

    with pytest.raises(HTTPException) as exc:
        await purchase_svc.convert_pr_to_po(db, actor, pr.id)

    assert exc.value.status_code == 422
    assert exc.value.detail == "pr.items_missing_supplier"


async def test_preview_pr_conversion_returns_supplier_groups(seeded_db_session):
    db = seeded_db_session
    actor = await _get_user(db, "alice")
    s1 = await _get_supplier(db, "SUP-DELL")
    s2 = await _get_supplier(db, "SUP-LENOVO")
    pr = await purchase_svc.create_pr(
        db,
        actor,
        PRCreateIn(
            title="Preview test",
            business_reason="Testing",
            currency="CNY",
            items=[
                _pr_item(1, "Server", "1", "1000", supplier_id=s1.id),
                _pr_item(2, "Server-2", "2", "1500", supplier_id=s1.id),
                _pr_item(3, "Laptop", "1", "2000", supplier_id=s2.id),
            ],
        ),
    )
    await _mark_pr_approved(db, pr)

    groups = await purchase_svc.preview_pr_conversion(db, actor, pr.id)

    assert len(groups) == 2
    by_supplier = {g["supplier_id"]: g for g in groups}
    assert by_supplier[s1.id]["item_count"] == 2
    assert by_supplier[s1.id]["subtotal"] == Decimal("1000") + Decimal("3000")
    assert by_supplier[s2.id]["item_count"] == 1
    assert by_supplier[s2.id]["subtotal"] == Decimal("2000")

    refreshed_pr = await purchase_svc.get_pr(db, actor, pr.id)
    assert refreshed_pr.status == PRStatus.APPROVED.value


async def test_convert_pr_to_po_assigns_sequential_po_numbers(seeded_db_session):
    db = seeded_db_session
    actor = await _get_user(db, "alice")
    supplier = await _get_supplier(db)
    pr1 = await _create_pr(db, actor, supplier.id, title="Convert 1")
    pr2 = await _create_pr(db, actor, supplier.id, title="Convert 2")
    await _mark_pr_approved(db, pr1)
    await _mark_pr_approved(db, pr2)

    po1 = (await purchase_svc.convert_pr_to_po(db, actor, pr1.id))[0]
    po2 = (await purchase_svc.convert_pr_to_po(db, actor, pr2.id))[0]

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

    pos = await purchase_svc.convert_pr_to_po(db, actor, pr.id)
    po = pos[0]

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


async def test_polist_schema_exposes_created_at_for_frontend(seeded_db_session):
    from app.schemas import POListOut

    db = seeded_db_session
    actor = await _get_user(db, "alice")
    supplier = await _get_supplier(db)
    pr = await _create_pr(db, actor, supplier.id)
    await _mark_pr_approved(db, pr)
    po = (await purchase_svc.convert_pr_to_po(db, actor, pr.id))[0]

    serialised = POListOut.model_validate(po).model_dump()
    assert "created_at" in serialised
    assert "updated_at" in serialised
    assert serialised["created_at"] is not None


async def test_polist_schema_includes_supplier_and_pr_metadata(seeded_db_session):
    from app.schemas import POListOut

    db = seeded_db_session
    actor = await _get_user(db, "alice")
    supplier = await _get_supplier(db)
    pr = await _create_pr(db, actor, supplier.id)
    await _mark_pr_approved(db, pr)
    pos = await purchase_svc.list_pos(db, actor)
    pos_for_pr = [p for p in pos if p.pr_id == pr.id]
    if not pos_for_pr:
        await purchase_svc.convert_pr_to_po(db, actor, pr.id)
        pos = await purchase_svc.list_pos(db, actor)
        pos_for_pr = [p for p in pos if p.pr_id == pr.id]
    assert pos_for_pr, "expected at least one PO in list for the PR"
    po = pos_for_pr[0]

    serialised = POListOut.model_validate(po).model_dump()

    assert serialised["supplier_id"] == supplier.id
    assert serialised["supplier_name"] == supplier.name
    assert serialised["supplier_code"] == supplier.code
    assert serialised["pr_number"] == pr.pr_number
    assert "amount_paid" in serialised
    assert "amount_invoiced" in serialised
    assert "qty_received" in serialised
    assert "source_type" in serialised


def test_pr_conversion_preview_group_schema_shape():
    from app.schemas import PRConversionPreviewGroup

    fields = set(PRConversionPreviewGroup.model_fields.keys())
    assert fields == {
        "supplier_id",
        "supplier_name",
        "supplier_code",
        "item_count",
        "subtotal",
        "items",
    }, (
        "PRConversionPreviewGroup must NOT contain PO-specific fields. "
        "v0.9.22 regression: amount_paid / amount_invoiced / created_at were "
        "accidentally appended and caused a 500 ResponseValidationError on "
        "GET /purchase-requisitions/{id}/conversion-preview."
    )


async def _create_pr_with_one_eligible_item(seeded_db_session):
    db = seeded_db_session
    actor = await _get_user(db, "alice")
    supplier = await _get_supplier(db)
    item = await _get_item(db)
    pr = await purchase_svc.create_pr(
        db,
        actor,
        PRCreateIn(
            title="Quote candidate test",
            business_reason="Testing",
            currency="CNY",
            items=[
                PRItemIn(
                    line_no=1,
                    item_id=item.id,
                    item_name=item.name,
                    qty=Decimal("3"),
                    unit_price=Decimal("250"),
                    supplier_id=supplier.id,
                ),
            ],
        ),
    )
    return db, actor, supplier, item, pr


async def test_list_pr_quote_candidates_returns_eligible_lines(seeded_db_session):
    db, actor, supplier, item, pr = await _create_pr_with_one_eligible_item(seeded_db_session)

    candidates = await purchase_svc.list_pr_quote_candidates(db, actor, pr.id)

    assert len(candidates) == 1
    c = candidates[0]
    assert c["item_id"] == item.id
    assert c["supplier_id"] == supplier.id
    assert c["unit_price"] == Decimal("250")
    assert c["already_exists"] is False
    assert c["already_up_to_date"] is False
    assert c["source_ref"] == f"{pr.pr_number}-L1"


async def test_list_pr_quote_candidates_skips_lines_without_item_id(seeded_db_session):
    db = seeded_db_session
    actor = await _get_user(db, "alice")
    supplier = await _get_supplier(db)
    pr = await purchase_svc.create_pr(
        db,
        actor,
        PRCreateIn(
            title="No item id",
            business_reason="Testing",
            currency="CNY",
            items=[
                PRItemIn(
                    line_no=1,
                    item_name="Free-text item without SKU",
                    qty=Decimal("1"),
                    unit_price=Decimal("100"),
                    supplier_id=supplier.id,
                ),
            ],
        ),
    )

    candidates = await purchase_svc.list_pr_quote_candidates(db, actor, pr.id)
    assert candidates == []


async def test_save_pr_supplier_quotes_creates_record_and_is_idempotent(seeded_db_session):
    from app.models import SKUPriceRecord

    db, actor, supplier, item, pr = await _create_pr_with_one_eligible_item(seeded_db_session)

    written = await purchase_svc.save_pr_supplier_quotes(db, actor, pr.id)
    assert len(written) == 1
    rec = written[0]
    assert rec.item_id == item.id
    assert rec.supplier_id == supplier.id
    assert rec.price == Decimal("250")
    assert rec.source_type == "supplier_quote"
    assert rec.source_ref == f"{pr.pr_number}-L1"

    written_again = await purchase_svc.save_pr_supplier_quotes(db, actor, pr.id)
    assert len(written_again) == 1
    assert written_again[0].id == rec.id

    rows = (
        (
            await db.execute(
                select(SKUPriceRecord).where(SKUPriceRecord.source_ref == f"{pr.pr_number}-L1")
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 1


async def test_save_pr_supplier_quotes_updates_when_price_changes(seeded_db_session):
    from app.models import PRItem, SKUPriceRecord

    db, actor, _supplier, _item, pr = await _create_pr_with_one_eligible_item(seeded_db_session)

    await purchase_svc.save_pr_supplier_quotes(db, actor, pr.id)

    pr_item = (
        await db.execute(select(PRItem).where(PRItem.pr_id == pr.id, PRItem.line_no == 1))
    ).scalar_one()
    pr_item.unit_price = Decimal("280")
    await db.flush()

    written = await purchase_svc.save_pr_supplier_quotes(db, actor, pr.id)
    assert len(written) == 1
    assert written[0].price == Decimal("280")

    rows = (
        (
            await db.execute(
                select(SKUPriceRecord).where(SKUPriceRecord.source_ref == f"{pr.pr_number}-L1")
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 1
    assert rows[0].price == Decimal("280")


async def test_save_pr_supplier_quotes_respects_line_filter(seeded_db_session):
    db = seeded_db_session
    actor = await _get_user(db, "alice")
    supplier = await _get_supplier(db)
    item = await _get_item(db)
    pr = await purchase_svc.create_pr(
        db,
        actor,
        PRCreateIn(
            title="Two-line filter test",
            business_reason="Testing",
            currency="CNY",
            items=[
                PRItemIn(
                    line_no=1,
                    item_id=item.id,
                    item_name=item.name,
                    qty=Decimal("1"),
                    unit_price=Decimal("100"),
                    supplier_id=supplier.id,
                ),
                PRItemIn(
                    line_no=2,
                    item_id=item.id,
                    item_name=item.name,
                    qty=Decimal("1"),
                    unit_price=Decimal("200"),
                    supplier_id=supplier.id,
                ),
            ],
        ),
    )

    written = await purchase_svc.save_pr_supplier_quotes(db, actor, pr.id, selected_line_nos=[1])
    assert len(written) == 1
    assert written[0].source_ref == f"{pr.pr_number}-L1"


async def _make_requester(seeded_db_session) -> User:
    db = seeded_db_session
    user = (
        (await db.execute(select(User).where(User.role == UserRole.REQUESTER.value)))
        .scalars()
        .first()
    )
    if user is not None:
        return user
    company = (await db.execute(select(Company))).scalars().first()
    user = User(
        username=f"scoped-req-{uuid4().hex[:6]}",
        email=f"scoped-req-{uuid4().hex[:6]}@test.local",
        display_name="Scoped Requester",
        password_hash="test",
        role=UserRole.REQUESTER.value,
        company_id=company.id,
        preferred_locale="zh-CN",
    )
    db.add(user)
    await db.flush()
    return user


async def test_requester_sees_own_prs_only_by_default(seeded_db_session):
    db = seeded_db_session
    user = await _make_requester(db)
    supplier = await _get_supplier(db)
    other = await _get_user(db, "bob")
    ctx1 = await _find_or_create_cost_center(db, "CC-SCOPE1")
    ctx2 = await _find_or_create_cost_center(db, "CC-SCOPE2")

    my_pr = await _create_pr_in_context(db, user, supplier.id, cost_center_id=ctx1.id)
    other_pr = await _create_pr_in_context(db, other, supplier.id, cost_center_id=ctx2.id)

    prs = await purchase_svc.list_prs_for_user(db, user)

    ids = {p.id for p in prs}
    assert my_pr.id in ids
    assert other_pr.id not in ids, (
        "requester without cost_center/department bindings should only see own PRs"
    )


async def _find_or_create_cost_center(db, code: str):
    existing = (
        await db.execute(select(CostCenter).where(CostCenter.code == code))
    ).scalar_one_or_none()
    if existing:
        return existing
    cc = CostCenter(code=code, label_zh=code, label_en=code)
    db.add(cc)
    await db.flush()
    return cc


async def _find_or_create_department(db, code: str, company_id=None):
    dept = (
        await db.execute(select(Department).where(Department.code == code))
    ).scalar_one_or_none()
    if dept:
        return dept
    if company_id is None:
        company = (
            (await db.execute(select(Company).where(Company.is_enabled.is_(True))))
            .scalars()
            .first()
        )
        company_id = company.id
    dept = Department(code=code, name_zh=code, name_en=code, company_id=company_id)
    db.add(dept)
    await db.flush()
    return dept


async def _create_pr_in_context(
    db, actor: User, supplier_id, *, cost_center_id=None, department_id=None
):
    pr = PurchaseRequisition(
        pr_number=f"PR-{uuid4().hex[:6]}",
        title="Scoping test",
        business_reason="Testing",
        status=PRStatus.APPROVED.value,
        requester_id=actor.id,
        company_id=actor.company_id,
        department_id=department_id or actor.department_id,
        cost_center_id=cost_center_id,
        currency="CNY",
        total_amount=Decimal("1000"),
    )
    db.add(pr)
    await db.flush()
    return pr


async def test_requester_with_cost_center_sees_that_cost_center_pr(seeded_db_session):
    db = seeded_db_session
    user = await _make_requester(db)
    other = await _get_user(db, "bob")
    supplier = await _get_supplier(db)
    cc = await _find_or_create_cost_center(db, "CC-FINANCE")

    await db.execute(user_cost_centers.insert().values(user_id=user.id, cost_center_id=cc.id))
    await db.flush()

    in_scope_pr = await _create_pr_in_context(db, other, supplier.id, cost_center_id=cc.id)
    other_cc = await _find_or_create_cost_center(db, "CC-OTHER")
    out_pr = await _create_pr_in_context(db, other, supplier.id, cost_center_id=other_cc.id)

    prs = await purchase_svc.list_prs_for_user(db, user)
    ids = {p.id for p in prs}
    assert in_scope_pr.id in ids, "requester should see PR with matching cost center"
    assert out_pr.id not in ids, "requester should not see PR with unrelated cost center"


async def test_requester_with_department_sees_that_department_pr(seeded_db_session):
    db = seeded_db_session
    user = await _make_requester(db)
    other = await _get_user(db, "bob")
    supplier = await _get_supplier(db)
    dept = await _find_or_create_department(db, "DEPT-ENG")

    await db.execute(user_departments.insert().values(user_id=user.id, department_id=dept.id))
    await db.flush()

    in_scope_pr = await _create_pr_in_context(db, other, supplier.id, department_id=dept.id)
    other_dept = await _find_or_create_department(db, "DEPT-SALES")
    out_pr = await _create_pr_in_context(db, other, supplier.id, department_id=other_dept.id)

    prs = await purchase_svc.list_prs_for_user(db, user)
    ids = {p.id for p in prs}
    assert in_scope_pr.id in ids
    assert out_pr.id not in ids


async def test_requester_cost_center_scoping_is_or_not_and(seeded_db_session):
    db = seeded_db_session
    user = await _make_requester(db)
    other = await _get_user(db, "bob")
    supplier = await _get_supplier(db)
    cc = await _find_or_create_cost_center(db, "CC-OR-TEST")
    dept = await _find_or_create_department(db, "DEPT-OR-TEST")

    await db.execute(user_cost_centers.insert().values(user_id=user.id, cost_center_id=cc.id))
    await db.execute(user_departments.insert().values(user_id=user.id, department_id=dept.id))
    await db.flush()

    pr_cc = await _create_pr_in_context(db, other, supplier.id, cost_center_id=cc.id)
    pr_dept = await _create_pr_in_context(db, other, supplier.id, department_id=dept.id)
    unrelated_cc = await _find_or_create_cost_center(db, "CC-UNRELATED")
    pr_unrelated = await _create_pr_in_context(
        db, other, supplier.id, cost_center_id=unrelated_cc.id
    )

    prs = await purchase_svc.list_prs_for_user(db, user)
    ids = {p.id for p in prs}
    assert pr_cc.id in ids, "cost-center match should be visible"
    assert pr_dept.id in ids, "department match should be visible"
    assert pr_unrelated.id not in ids, "unrelated should still be hidden"


async def test_admin_not_affected_by_scoping(seeded_db_session):
    db = seeded_db_session
    admin = await _get_user(db, "admin")
    supplier = await _get_supplier(db)
    cc = await _find_or_create_cost_center(db, "CC-ADMINTEST")

    await _create_pr_in_context(db, admin, supplier.id, cost_center_id=cc.id)

    prs = await purchase_svc.list_prs_for_user(db, admin)
    assert len(prs) >= 1, "admin should see all PRs regardless of scoping"
