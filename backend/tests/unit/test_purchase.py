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
    FulfillmentType,
    Item,
    POStatus,
    PRFulfillmentLink,
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


async def test_get_pr_allows_other_buyer(seeded_db_session):
    """IT_BUYER has full access to all PRs per permission matrix (decision 0020)."""
    db = seeded_db_session
    owner = await _get_user(db, "alice")
    other_buyer = await _create_buyer(db, "zoe", owner.company_id, owner.department_id)
    supplier = await _get_supplier(db)
    pr = await _create_pr(db, owner, supplier.id)

    loaded = await purchase_svc.get_pr(db, other_buyer, pr.id)
    assert loaded.id == pr.id


async def test_get_pr_allows_department_manager_for_same_department(seeded_db_session):
    db = seeded_db_session
    owner = await _get_user(db, "alice")
    manager = await _get_user(db, "bob")
    supplier = await _get_supplier(db)
    pr = await _create_pr(db, owner, supplier.id)

    loaded = await purchase_svc.get_pr(db, manager, pr.id)

    assert loaded.id == pr.id


async def test_list_prs_for_buyer_returns_all_prs(seeded_db_session):
    db = seeded_db_session
    alice = await _get_user(db, "alice")
    dave = await _get_user(db, "dave")
    supplier = await _get_supplier(db)
    alice_pr = await _create_pr(db, alice, supplier.id, title="Alice PR")
    dave_pr = await _create_pr(db, dave, supplier.id, title="Dave PR")

    prs = await purchase_svc.list_prs_for_user(db, alice)
    pr_ids = [pr.id for pr in prs]

    assert alice_pr.id in pr_ids
    assert dave_pr.id in pr_ids


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


async def test_requester_sees_only_own_prs_not_cost_center(seeded_db_session):
    db = seeded_db_session
    user = await _make_requester(db)
    other = await _get_user(db, "bob")
    supplier = await _get_supplier(db)
    cc = await _find_or_create_cost_center(db, "CC-FINANCE")

    await db.execute(user_cost_centers.insert().values(user_id=user.id, cost_center_id=cc.id))
    await db.flush()

    other_pr = await _create_pr_in_context(db, other, supplier.id, cost_center_id=cc.id)
    own_pr = await _create_pr_in_context(db, user, supplier.id, cost_center_id=cc.id)

    prs = await purchase_svc.list_prs_for_user(db, user)
    ids = {p.id for p in prs}
    assert own_pr.id in ids, "requester should see own PR"
    assert other_pr.id not in ids, (
        "requester should NOT see other's PR even with matching cost center"
    )


async def test_requester_sees_only_own_prs_not_department(seeded_db_session):
    db = seeded_db_session
    user = await _make_requester(db)
    other = await _get_user(db, "bob")
    supplier = await _get_supplier(db)
    dept = await _find_or_create_department(db, "DEPT-ENG")

    await db.execute(user_departments.insert().values(user_id=user.id, department_id=dept.id))
    await db.flush()

    other_pr = await _create_pr_in_context(db, other, supplier.id, department_id=dept.id)
    own_pr = await _create_pr_in_context(db, user, supplier.id, department_id=dept.id)

    prs = await purchase_svc.list_prs_for_user(db, user)
    ids = {p.id for p in prs}
    assert own_pr.id in ids
    assert other_pr.id not in ids


async def test_requester_only_sees_own_prs(seeded_db_session):
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
    own_pr = await _create_pr_in_context(db, user, supplier.id, cost_center_id=cc.id)

    prs = await purchase_svc.list_prs_for_user(db, user)
    ids = {p.id for p in prs}
    assert own_pr.id in ids, "requester should see own PR"
    assert pr_cc.id not in ids, "requester should NOT see other's PR by cost center"
    assert pr_dept.id not in ids, "requester should NOT see other's PR by department"


async def test_admin_not_affected_by_scoping(seeded_db_session):
    db = seeded_db_session
    admin = await _get_user(db, "admin")
    supplier = await _get_supplier(db)
    cc = await _find_or_create_cost_center(db, "CC-ADMINTEST")

    await _create_pr_in_context(db, admin, supplier.id, cost_center_id=cc.id)

    prs = await purchase_svc.list_prs_for_user(db, admin)
    assert len(prs) >= 1, "admin should see all PRs regardless of scoping"


async def test_add_collaborator_makes_pr_visible(seeded_db_session):
    db = seeded_db_session
    alice = await _get_user(db, "alice")
    supplier = await _get_supplier(db)
    pr = await _create_pr(db, alice, supplier.id, title="Collab PR")

    requester = await _make_requester(db)
    prs_before = await purchase_svc.list_prs_for_user(db, requester)
    assert pr.id not in {p.id for p in prs_before}

    await purchase_svc.add_collaborator(db, alice, pr.id, requester.id)

    prs_after = await purchase_svc.list_prs_for_user(db, requester)
    assert pr.id in {p.id for p in prs_after}


async def test_remove_collaborator_hides_pr(seeded_db_session):
    db = seeded_db_session
    alice = await _get_user(db, "alice")
    supplier = await _get_supplier(db)
    pr = await _create_pr(db, alice, supplier.id, title="Collab Remove PR")

    requester = await _make_requester(db)
    await purchase_svc.add_collaborator(db, alice, pr.id, requester.id)

    prs = await purchase_svc.list_prs_for_user(db, requester)
    assert pr.id in {p.id for p in prs}

    await purchase_svc.remove_collaborator(db, alice, pr.id, requester.id)

    prs_after = await purchase_svc.list_prs_for_user(db, requester)
    assert pr.id not in {p.id for p in prs_after}


async def test_add_collaborator_is_idempotent(seeded_db_session):
    db = seeded_db_session
    alice = await _get_user(db, "alice")
    supplier = await _get_supplier(db)
    pr = await _create_pr(db, alice, supplier.id, title="Collab Idem PR")

    requester = await _make_requester(db)
    await purchase_svc.add_collaborator(db, alice, pr.id, requester.id)
    await purchase_svc.add_collaborator(db, alice, pr.id, requester.id)

    collabs = await purchase_svc.list_collaborators(db, pr.id)
    assert len(collabs) == 1


async def test_delete_pr_allows_draft(seeded_db_session):
    db = seeded_db_session
    actor = await _get_user(db, "alice")
    supplier = await _get_supplier(db)
    pr = await _create_pr(db, actor, supplier.id, title="Draft PR")
    assert pr.status == PRStatus.DRAFT.value

    await purchase_svc.delete_pr(db, actor, pr.id)

    with pytest.raises(HTTPException) as exc:
        await purchase_svc.get_pr(db, actor, pr.id)
    assert exc.value.status_code == 404


async def test_delete_pr_allows_returned(seeded_db_session):
    db = seeded_db_session
    actor = await _get_user(db, "alice")
    supplier = await _get_supplier(db)
    pr = await _create_pr(db, actor, supplier.id, title="Returned PR")
    pr.status = PRStatus.RETURNED.value
    await db.commit()

    await purchase_svc.delete_pr(db, actor, pr.id)

    with pytest.raises(HTTPException) as exc:
        await purchase_svc.get_pr(db, actor, pr.id)
    assert exc.value.status_code == 404


async def test_delete_pr_allows_rejected(seeded_db_session):
    db = seeded_db_session
    actor = await _get_user(db, "alice")
    supplier = await _get_supplier(db)
    pr = await _create_pr(db, actor, supplier.id, title="Rejected PR")
    pr.status = PRStatus.REJECTED.value
    await db.commit()

    await purchase_svc.delete_pr(db, actor, pr.id)

    with pytest.raises(HTTPException) as exc:
        await purchase_svc.get_pr(db, actor, pr.id)
    assert exc.value.status_code == 404


async def test_delete_pr_rejects_submitted(seeded_db_session):
    db = seeded_db_session
    actor = await _get_user(db, "alice")
    supplier = await _get_supplier(db)
    pr = await _create_pr(db, actor, supplier.id, title="Submitted PR")
    pr.status = PRStatus.SUBMITTED.value
    await db.commit()

    with pytest.raises(HTTPException) as exc:
        await purchase_svc.delete_pr(db, actor, pr.id)
    assert exc.value.status_code == 409
    assert exc.value.detail == "pr.cannot_delete_active"


async def test_delete_pr_rejects_approved(seeded_db_session):
    db = seeded_db_session
    actor = await _get_user(db, "alice")
    supplier = await _get_supplier(db)
    pr = await _create_pr(db, actor, supplier.id, title="Approved PR")
    pr.status = PRStatus.APPROVED.value
    await db.commit()

    with pytest.raises(HTTPException) as exc:
        await purchase_svc.delete_pr(db, actor, pr.id)
    assert exc.value.status_code == 409


async def test_delete_pr_requester_can_delete_own(seeded_db_session):
    db = seeded_db_session
    requester = await _make_requester(db)
    supplier = await _get_supplier(db)
    pr = await _create_pr(db, requester, supplier.id, title="Requester Own PR")
    pr.status = PRStatus.RETURNED.value
    await db.commit()

    await purchase_svc.delete_pr(db, requester, pr.id)

    with pytest.raises(HTTPException) as exc:
        await purchase_svc.get_pr(db, requester, pr.id)
    assert exc.value.status_code == 404


async def test_pr_number_no_collision_after_delete(seeded_db_session):
    db = seeded_db_session
    actor = await _get_user(db, "alice")
    supplier = await _get_supplier(db)

    pr1 = await _create_pr(db, actor, supplier.id, title="PR A")
    pr2 = await _create_pr(db, actor, supplier.id, title="PR B")
    pr3 = await _create_pr(db, actor, supplier.id, title="PR C")
    numbers = {pr1.pr_number, pr2.pr_number, pr3.pr_number}
    assert len(numbers) == 3

    await purchase_svc.delete_pr(db, actor, pr2.id)

    pr4 = await _create_pr(db, actor, supplier.id, title="PR D")
    assert pr4.pr_number not in {pr1.pr_number, pr3.pr_number}
    assert pr4.pr_number > pr3.pr_number


async def test_pr_number_uses_max_suffix_not_count(seeded_db_session):
    db = seeded_db_session
    actor = await _get_user(db, "alice")
    supplier = await _get_supplier(db)

    first = await _create_pr(db, actor, supplier.id, title="First")
    second = await _create_pr(db, actor, supplier.id, title="Second")
    third = await _create_pr(db, actor, supplier.id, title="Third")

    # Delete the middle one — count drops but max suffix is unchanged
    await purchase_svc.delete_pr(db, actor, second.id)

    fourth = await _create_pr(db, actor, supplier.id, title="Fourth")
    # COUNT+1 would have produced third's number (collision); max+1 must exceed third
    assert int(fourth.pr_number[-4:]) == int(third.pr_number[-4:]) + 1
    assert fourth.pr_number not in {first.pr_number, third.pr_number}


async def test_delete_po_succeeds_when_no_downstream(seeded_db_session):
    db = seeded_db_session
    actor = await _get_user(db, "alice")
    supplier = await _get_supplier(db)
    pr = await _create_pr(db, actor, supplier.id, title="PO Delete Test")
    await _mark_pr_approved(db, pr)
    pos = await purchase_svc.convert_pr_to_po(db, actor, pr.id)
    po = pos[0]

    await purchase_svc.delete_po(db, actor, po.id)

    with pytest.raises(HTTPException) as exc:
        await purchase_svc.get_po(db, po.id)
    assert exc.value.status_code == 404


async def test_delete_po_resets_pr_status_when_all_links_gone(seeded_db_session):
    db = seeded_db_session
    actor = await _get_user(db, "alice")
    supplier = await _get_supplier(db)
    pr = await _create_pr(db, actor, supplier.id, title="Status Reset Test")
    await _mark_pr_approved(db, pr)
    pos = await purchase_svc.convert_pr_to_po(db, actor, pr.id)

    pr_after_convert = await purchase_svc.get_pr(db, actor, pr.id)
    assert pr_after_convert.status == PRStatus.CONVERTED.value

    pr_id = pr.id
    await purchase_svc.delete_po(db, actor, pos[0].id)
    db.expire_all()

    pr_after_delete = await purchase_svc.get_pr(db, actor, pr_id)
    assert pr_after_delete.status == PRStatus.APPROVED.value

    links_count = (
        await db.execute(
            select(PRFulfillmentLink).where(
                PRFulfillmentLink.pr_item_id.in_([i.id for i in pr_after_delete.items])
            )
        )
    ).all()
    assert len(links_count) == 0


async def test_delete_po_partial_resets_to_partially_converted(seeded_db_session):
    db = seeded_db_session
    actor = await _get_user(db, "alice")
    s1 = await _get_supplier(db, "SUP-DELL")
    s2 = await _get_supplier(db, "SUP-LENOVO")
    pr = await purchase_svc.create_pr(
        db,
        actor,
        PRCreateIn(
            title="Two-supplier PR",
            business_reason="testing partial deletion",
            currency="CNY",
            items=[
                _pr_item(1, "ItemA", "1", "100", supplier_id=s1.id),
                _pr_item(2, "ItemB", "1", "200", supplier_id=s2.id),
            ],
        ),
    )
    await _mark_pr_approved(db, pr)
    pos = await purchase_svc.convert_pr_to_po(db, actor, pr.id)
    assert len(pos) == 2

    pr_id = pr.id
    await purchase_svc.delete_po(db, actor, pos[0].id)
    db.expire_all()

    pr_after = await purchase_svc.get_pr(db, actor, pr_id)
    assert pr_after.status == PRStatus.PARTIALLY_CONVERTED.value


async def test_delete_po_blocked_by_shipment(seeded_db_session):
    from decimal import Decimal

    from app.services import flow as flow_svc

    db = seeded_db_session
    actor = await _get_user(db, "alice")
    supplier = await _get_supplier(db)
    pr = await _create_pr(db, actor, supplier.id, title="PO Shipment Block")
    await _mark_pr_approved(db, pr)
    po = (await purchase_svc.convert_pr_to_po(db, actor, pr.id))[0]

    await flow_svc.create_shipment(
        db,
        actor,
        po.id,
        items_in=[{"po_item_id": po.items[0].id, "qty_shipped": Decimal("1")}],
    )

    with pytest.raises(HTTPException) as exc:
        await purchase_svc.delete_po(db, actor, po.id)
    assert exc.value.status_code == 409
    assert exc.value.detail == "po.cannot_delete_has_shipments"


async def test_delete_po_blocked_by_contract(seeded_db_session):
    from decimal import Decimal

    from app.services import flow as flow_svc

    db = seeded_db_session
    actor = await _get_user(db, "alice")
    supplier = await _get_supplier(db)
    pr = await _create_pr(db, actor, supplier.id, title="PO Contract Block")
    await _mark_pr_approved(db, pr)
    po = (await purchase_svc.convert_pr_to_po(db, actor, pr.id))[0]

    await flow_svc.create_contract(
        db, actor, po.id, title="Blocking Contract", total_amount=Decimal("100")
    )

    with pytest.raises(HTTPException) as exc:
        await purchase_svc.delete_po(db, actor, po.id)
    assert exc.value.status_code == 409
    assert exc.value.detail == "po.cannot_delete_has_contracts"


async def test_delete_po_not_found(seeded_db_session):
    from uuid import uuid4

    db = seeded_db_session
    actor = await _get_user(db, "alice")
    with pytest.raises(HTTPException) as exc:
        await purchase_svc.delete_po(db, actor, uuid4())
    assert exc.value.status_code == 404


async def _count_links_for_pr(db, pr_id) -> list[PRFulfillmentLink]:
    rows = (
        await db.execute(
            select(PRFulfillmentLink)
            .join(PRFulfillmentLink.pr_item)
            .where(PRFulfillmentLink.pr_item.has(pr_id=pr_id))
        )
    ).scalars().all()
    return list(rows)


async def test_convert_pr_to_po_creates_equivalent_links(seeded_db_session):
    db = seeded_db_session
    actor = await _get_user(db, "alice")
    supplier = await _get_supplier(db)
    pr = await _create_pr(db, actor, supplier.id)
    await _mark_pr_approved(db, pr)

    await purchase_svc.convert_pr_to_po(db, actor, pr.id)

    links = await _count_links_for_pr(db, pr.id)
    assert len(links) == len(pr.items)
    assert all(link.fulfillment_type == FulfillmentType.EQUIVALENT.value for link in links)
    assert all(link.qty_contribution > 0 for link in links)


async def test_convert_pr_to_po_partial_creates_only_selected_items(seeded_db_session):
    db = seeded_db_session
    actor = await _get_user(db, "alice")
    s1 = await _get_supplier(db, "SUP-DELL")
    s2 = await _get_supplier(db, "SUP-LENOVO")
    pr = await purchase_svc.create_pr(
        db,
        actor,
        PRCreateIn(
            title="Partial PR",
            business_reason="testing partial conversion",
            currency="CNY",
            items=[
                _pr_item(1, "ItemA", "1", "100", supplier_id=s1.id),
                _pr_item(2, "ItemB", "2", "200", supplier_id=s1.id),
                _pr_item(3, "ItemC", "1", "300", supplier_id=s2.id),
            ],
        ),
    )
    await _mark_pr_approved(db, pr)

    selected = [i.id for i in pr.items if i.line_no == 1]
    pos = await purchase_svc.convert_pr_to_po_partial(db, actor, pr.id, selected)

    refreshed_pr = await purchase_svc.get_pr(db, actor, pr.id)
    links = await _count_links_for_pr(db, pr.id)

    assert len(pos) == 1
    assert len(pos[0].items) == 1
    assert pos[0].supplier_id == s1.id
    assert len(links) == 1
    assert refreshed_pr.status == PRStatus.PARTIALLY_CONVERTED.value


async def test_convert_pr_to_po_partial_then_full_marks_converted(seeded_db_session):
    db = seeded_db_session
    actor = await _get_user(db, "alice")
    s1 = await _get_supplier(db, "SUP-DELL")
    s2 = await _get_supplier(db, "SUP-LENOVO")
    pr = await purchase_svc.create_pr(
        db,
        actor,
        PRCreateIn(
            title="Two-step PR",
            business_reason="partial then full",
            currency="CNY",
            items=[
                _pr_item(1, "ItemA", "1", "100", supplier_id=s1.id),
                _pr_item(2, "ItemB", "1", "200", supplier_id=s2.id),
            ],
        ),
    )
    await _mark_pr_approved(db, pr)

    line1_ids = [i.id for i in pr.items if i.line_no == 1]
    await purchase_svc.convert_pr_to_po_partial(db, actor, pr.id, line1_ids)
    pr_after_partial = await purchase_svc.get_pr(db, actor, pr.id)
    assert pr_after_partial.status == PRStatus.PARTIALLY_CONVERTED.value

    await purchase_svc.convert_pr_to_po(db, actor, pr.id)
    pr_after_full = await purchase_svc.get_pr(db, actor, pr.id)
    assert pr_after_full.status == PRStatus.CONVERTED.value

    links = await _count_links_for_pr(db, pr.id)
    assert len(links) == 2


async def test_convert_pr_to_po_partial_rejects_already_converted_item(seeded_db_session):
    db = seeded_db_session
    actor = await _get_user(db, "alice")
    s1 = await _get_supplier(db, "SUP-DELL")
    pr = await purchase_svc.create_pr(
        db,
        actor,
        PRCreateIn(
            title="Repeat PR",
            business_reason="reject duplicate",
            currency="CNY",
            items=[_pr_item(1, "ItemA", "1", "100", supplier_id=s1.id)],
        ),
    )
    await _mark_pr_approved(db, pr)
    pr_item_ids = [i.id for i in pr.items]
    await purchase_svc.convert_pr_to_po_partial(db, actor, pr.id, pr_item_ids)

    with pytest.raises(HTTPException) as exc:
        await purchase_svc.convert_pr_to_po_partial(db, actor, pr.id, pr_item_ids)
    assert exc.value.status_code == 409
    assert exc.value.detail == "pr.partial_already_converted"


async def test_convert_pr_to_po_partial_rejects_unknown_item(seeded_db_session):
    db = seeded_db_session
    actor = await _get_user(db, "alice")
    supplier = await _get_supplier(db)
    pr = await _create_pr(db, actor, supplier.id)
    await _mark_pr_approved(db, pr)

    with pytest.raises(HTTPException) as exc:
        await purchase_svc.convert_pr_to_po_partial(db, actor, pr.id, [uuid4()])
    assert exc.value.status_code == 422
    assert exc.value.detail == "pr.partial_unknown_item"


async def test_convert_pr_to_po_partial_rejects_empty_list(seeded_db_session):
    db = seeded_db_session
    actor = await _get_user(db, "alice")
    supplier = await _get_supplier(db)
    pr = await _create_pr(db, actor, supplier.id)
    await _mark_pr_approved(db, pr)

    with pytest.raises(HTTPException) as exc:
        await purchase_svc.convert_pr_to_po_partial(db, actor, pr.id, [])
    assert exc.value.status_code == 422
    assert exc.value.detail == "pr.partial_no_items"


async def test_convert_pr_to_po_after_full_rejects_already_converted(seeded_db_session):
    db = seeded_db_session
    actor = await _get_user(db, "alice")
    supplier = await _get_supplier(db)
    pr = await _create_pr(db, actor, supplier.id)
    await _mark_pr_approved(db, pr)
    await purchase_svc.convert_pr_to_po(db, actor, pr.id)

    with pytest.raises(HTTPException) as exc:
        await purchase_svc.convert_pr_to_po(db, actor, pr.id)
    assert exc.value.status_code == 409


async def test_create_fulfillment_link_for_downgrade(seeded_db_session):
    db = seeded_db_session
    actor = await _get_user(db, "alice")
    supplier = await _get_supplier(db)
    pr = await _create_pr(db, actor, supplier.id)
    await _mark_pr_approved(db, pr)
    pos = await purchase_svc.convert_pr_to_po(db, actor, pr.id)
    po = pos[0]

    new_po_item = await purchase_svc.add_supplementary_po_item(
        db,
        actor,
        po_id=po.id,
        item_name="Server X (missing A part)",
        qty=Decimal("4"),
        unit_price=Decimal("500"),
    )
    link = await purchase_svc.create_fulfillment_link(
        db,
        actor,
        po_item_id=new_po_item.id,
        pr_item_id=pr.items[0].id,
        fulfillment_type="downgraded",
        qty_contribution=Decimal("4"),
        deviation_note="A part out of stock; sourced separately",
    )

    assert link.fulfillment_type == "downgraded"
    assert link.qty_contribution == Decimal("4")
    assert link.deviation_note == "A part out of stock; sourced separately"


async def test_create_fulfillment_link_rejects_duplicate(seeded_db_session):
    db = seeded_db_session
    actor = await _get_user(db, "alice")
    supplier = await _get_supplier(db)
    pr = await _create_pr(db, actor, supplier.id)
    await _mark_pr_approved(db, pr)
    pos = await purchase_svc.convert_pr_to_po(db, actor, pr.id)
    po_item = pos[0].items[0]

    with pytest.raises(HTTPException) as exc:
        await purchase_svc.create_fulfillment_link(
            db,
            actor,
            po_item_id=po_item.id,
            pr_item_id=pr.items[0].id,
            fulfillment_type="equivalent",
            qty_contribution=Decimal("1"),
        )
    assert exc.value.status_code == 409
    assert exc.value.detail == "fulfillment.link_already_exists"


async def test_create_fulfillment_link_rejects_invalid_type(seeded_db_session):
    db = seeded_db_session
    actor = await _get_user(db, "alice")
    supplier = await _get_supplier(db)
    pr = await _create_pr(db, actor, supplier.id)
    await _mark_pr_approved(db, pr)
    pos = await purchase_svc.convert_pr_to_po(db, actor, pr.id)
    new_po_item = await purchase_svc.add_supplementary_po_item(
        db, actor, po_id=pos[0].id, item_name="extra", qty=Decimal("1"), unit_price=Decimal("100")
    )

    with pytest.raises(HTTPException) as exc:
        await purchase_svc.create_fulfillment_link(
            db,
            actor,
            po_item_id=new_po_item.id,
            pr_item_id=pr.items[0].id,
            fulfillment_type="bogus_type",
            qty_contribution=Decimal("1"),
        )
    assert exc.value.status_code == 422
    assert exc.value.detail == "fulfillment.invalid_type"


async def test_create_fulfillment_link_enforces_soft_qty_limit(seeded_db_session):
    db = seeded_db_session
    actor = await _get_user(db, "alice")
    supplier = await _get_supplier(db)
    pr = await purchase_svc.create_pr(
        db,
        actor,
        PRCreateIn(
            title="Soft limit PR",
            business_reason="testing soft limit",
            currency="CNY",
            items=[_pr_item(1, "ItemA", "10", "100", supplier_id=supplier.id)],
        ),
    )
    await _mark_pr_approved(db, pr)
    pos = await purchase_svc.convert_pr_to_po(db, actor, pr.id)
    new_po_item = await purchase_svc.add_supplementary_po_item(
        db,
        actor,
        po_id=pos[0].id,
        item_name="Overage",
        qty=Decimal("100"),
        unit_price=Decimal("1"),
    )

    with pytest.raises(HTTPException) as exc:
        await purchase_svc.create_fulfillment_link(
            db,
            actor,
            po_item_id=new_po_item.id,
            pr_item_id=pr.items[0].id,
            fulfillment_type="equivalent",
            qty_contribution=Decimal("100"),
        )
    assert exc.value.status_code == 422
    assert exc.value.detail == "fulfillment.qty_exceeds_soft_limit"


async def test_update_fulfillment_link_changes_type_and_qty(seeded_db_session):
    db = seeded_db_session
    actor = await _get_user(db, "alice")
    supplier = await _get_supplier(db)
    pr = await _create_pr(db, actor, supplier.id)
    await _mark_pr_approved(db, pr)
    pos = await purchase_svc.convert_pr_to_po(db, actor, pr.id)
    existing_link = pos[0].items[0].fulfillment_links[0]

    updated = await purchase_svc.update_fulfillment_link(
        db,
        actor,
        existing_link.id,
        fulfillment_type="substitute",
        deviation_note="model switched due to stockout",
    )
    assert updated.fulfillment_type == "substitute"
    assert updated.deviation_note == "model switched due to stockout"


async def test_delete_fulfillment_link_recomputes_pr_status(seeded_db_session):
    db = seeded_db_session
    actor = await _get_user(db, "alice")
    supplier = await _get_supplier(db)
    pr = await _create_pr(db, actor, supplier.id)
    await _mark_pr_approved(db, pr)
    pos = await purchase_svc.convert_pr_to_po(db, actor, pr.id)
    pr_after_convert = await purchase_svc.get_pr(db, actor, pr.id)
    assert pr_after_convert.status == PRStatus.CONVERTED.value

    link_to_delete = pos[0].items[0].fulfillment_links[0]
    await purchase_svc.delete_fulfillment_link(db, actor, link_to_delete.id)

    pr_after_delete = await purchase_svc.get_pr(db, actor, pr.id)
    assert pr_after_delete.status in (
        PRStatus.PARTIALLY_CONVERTED.value,
        PRStatus.APPROVED.value,
    )


async def test_add_supplementary_po_item_with_link_marks_pr_item_context(
    seeded_db_session,
):
    db = seeded_db_session
    actor = await _get_user(db, "alice")
    supplier = await _get_supplier(db)
    pr = await _create_pr(db, actor, supplier.id)
    await _mark_pr_approved(db, pr)
    pos = await purchase_svc.convert_pr_to_po(db, actor, pr.id)

    pr_item_a = pr.items[0]
    new_po_item = await purchase_svc.add_supplementary_po_item(
        db,
        actor,
        po_id=pos[0].id,
        item_name="A part",
        qty=Decimal("4"),
        unit_price=Decimal("50"),
        supplementary_for_pr_item_id=pr_item_a.id,
        deviation_note="补充服务器缺少的 A 配件",
    )

    assert new_po_item.pr_item_id is None
    breakdown = await purchase_svc.get_pr_item_fulfillment_breakdown(db, pr_item_a.id)
    assert breakdown["supplementary"] == Decimal("4")

    from app.schemas import POItemOut

    serialized = POItemOut.model_validate(new_po_item)
    assert serialized.id == new_po_item.id
    assert serialized.item_name == "A part"
    assert isinstance(serialized.fulfillment_links, list)
    assert len(serialized.fulfillment_links) == 1
    assert serialized.fulfillment_links[0].fulfillment_type == "supplementary"


async def test_supplementary_po_item_rejects_pr_from_other_pr(seeded_db_session):
    db = seeded_db_session
    actor = await _get_user(db, "alice")
    supplier = await _get_supplier(db)
    pr1 = await _create_pr(db, actor, supplier.id)
    await _mark_pr_approved(db, pr1)
    pos = await purchase_svc.convert_pr_to_po(db, actor, pr1.id)

    pr2 = await _create_pr(db, actor, supplier.id)
    await _mark_pr_approved(db, pr2)
    other_pr_item_id = pr2.items[0].id

    with pytest.raises(HTTPException) as exc:
        await purchase_svc.add_supplementary_po_item(
            db,
            actor,
            po_id=pos[0].id,
            item_name="wrong-pr",
            qty=Decimal("1"),
            unit_price=Decimal("100"),
            supplementary_for_pr_item_id=other_pr_item_id,
        )
    assert exc.value.status_code == 422
    assert exc.value.detail == "fulfillment.supplementary_pr_mismatch"


async def test_pr_item_split_across_two_po_items(seeded_db_session):
    db = seeded_db_session
    actor = await _get_user(db, "alice")
    supplier = await _get_supplier(db)
    pr = await purchase_svc.create_pr(
        db,
        actor,
        PRCreateIn(
            title="Split PR",
            business_reason="testing split",
            currency="CNY",
            items=[_pr_item(1, "Server", "10", "1000", supplier_id=supplier.id)],
        ),
    )
    await _mark_pr_approved(db, pr)
    pos = await purchase_svc.convert_pr_to_po(db, actor, pr.id)
    extra_po_item = await purchase_svc.add_supplementary_po_item(
        db,
        actor,
        po_id=pos[0].id,
        item_name="Server (downgraded)",
        qty=Decimal("3"),
        unit_price=Decimal("800"),
    )

    breakdown_before = await purchase_svc.get_pr_item_fulfillment_breakdown(
        db, pr.items[0].id
    )
    assert breakdown_before["equivalent"] == Decimal("10")

    await purchase_svc.create_fulfillment_link(
        db,
        actor,
        po_item_id=extra_po_item.id,
        pr_item_id=pr.items[0].id,
        fulfillment_type="downgraded",
        qty_contribution=Decimal("3"),
    )

    breakdown_after = await purchase_svc.get_pr_item_fulfillment_breakdown(
        db, pr.items[0].id
    )
    assert breakdown_after["equivalent"] == Decimal("10")
    assert breakdown_after["downgraded"] == Decimal("3")


async def test_pr_detail_response_includes_fulfillment_breakdown(seeded_db_session):
    from app.schemas import PROut

    db = seeded_db_session
    actor = await _get_user(db, "alice")
    supplier = await _get_supplier(db)
    pr = await _create_pr(db, actor, supplier.id)
    await _mark_pr_approved(db, pr)
    await purchase_svc.convert_pr_to_po(db, actor, pr.id)
    pr_id = pr.id

    db.expire_all()
    refreshed = await purchase_svc.get_pr(db, actor, pr_id)
    out = PROut.model_validate(refreshed)

    for item in out.items:
        assert item.fulfilled_qty is not None
        assert item.is_fully_fulfilled is True
        assert item.fulfillment_breakdown is not None
        assert item.fulfillment_breakdown.get("equivalent", Decimal("0")) > 0


async def test_convert_pr_to_po_with_specs_partial_qty_and_type(seeded_db_session):
    from app.services.purchase import PRConvertSpec

    db = seeded_db_session
    actor = await _get_user(db, "alice")
    supplier = await _get_supplier(db)
    pr = await purchase_svc.create_pr(
        db,
        actor,
        PRCreateIn(
            title="Spec convert test",
            business_reason="testing qty split + type",
            currency="CNY",
            items=[_pr_item(1, "Server X", "64", "1000", supplier_id=supplier.id)],
        ),
    )
    await _mark_pr_approved(db, pr)

    pr_item_id = pr.items[0].id
    specs = [
        PRConvertSpec(
            pr_item_id=pr_item_id,
            qty=Decimal("32"),
            fulfillment_type="equivalent",
        ),
    ]
    pos = await purchase_svc.convert_pr_to_po_with_specs(db, actor, pr.id, specs)

    assert len(pos) == 1
    po = pos[0]
    assert len(po.items) == 1
    assert po.items[0].qty == Decimal("32")
    assert po.items[0].fulfillment_links[0].qty_contribution == Decimal("32")
    assert po.items[0].fulfillment_links[0].fulfillment_type == "equivalent"

    pr_after = await purchase_svc.get_pr(db, actor, pr.id)
    assert pr_after.status == PRStatus.PARTIALLY_CONVERTED.value


async def test_convert_pr_to_po_with_specs_then_downgrade_remainder(seeded_db_session):
    from app.services.purchase import PRConvertSpec

    db = seeded_db_session
    actor = await _get_user(db, "alice")
    supplier = await _get_supplier(db)
    pr = await purchase_svc.create_pr(
        db,
        actor,
        PRCreateIn(
            title="Two-pass convert",
            business_reason="32 equivalent + 32 downgraded",
            currency="CNY",
            items=[_pr_item(1, "Server X", "64", "1000", supplier_id=supplier.id)],
        ),
    )
    await _mark_pr_approved(db, pr)
    pr_item_id = pr.items[0].id

    await purchase_svc.convert_pr_to_po_with_specs(
        db,
        actor,
        pr.id,
        [PRConvertSpec(pr_item_id=pr_item_id, qty=Decimal("32"), fulfillment_type="equivalent")],
    )
    pos2 = await purchase_svc.convert_pr_to_po_with_specs(
        db,
        actor,
        pr.id,
        [
            PRConvertSpec(
                pr_item_id=pr_item_id,
                qty=Decimal("32"),
                fulfillment_type="downgraded",
                deviation_note="A part out of stock",
            )
        ],
    )

    assert len(pos2) == 1
    assert pos2[0].items[0].qty == Decimal("32")
    assert pos2[0].items[0].fulfillment_links[0].fulfillment_type == "downgraded"
    assert pos2[0].items[0].fulfillment_links[0].deviation_note == "A part out of stock"

    breakdown = await purchase_svc.get_pr_item_fulfillment_breakdown(db, pr_item_id)
    assert breakdown["equivalent"] == Decimal("32")
    assert breakdown["downgraded"] == Decimal("32")

    pr_after = await purchase_svc.get_pr(db, actor, pr.id)
    assert pr_after.status == PRStatus.CONVERTED.value


async def test_convert_pr_to_po_with_specs_rejects_overflow(seeded_db_session):
    from app.services.purchase import PRConvertSpec

    db = seeded_db_session
    actor = await _get_user(db, "alice")
    supplier = await _get_supplier(db)
    pr = await purchase_svc.create_pr(
        db,
        actor,
        PRCreateIn(
            title="Overflow test",
            business_reason="reject 1.5x soft limit",
            currency="CNY",
            items=[_pr_item(1, "Server", "10", "1000", supplier_id=supplier.id)],
        ),
    )
    await _mark_pr_approved(db, pr)

    with pytest.raises(HTTPException) as exc:
        await purchase_svc.convert_pr_to_po_with_specs(
            db,
            actor,
            pr.id,
            [
                PRConvertSpec(
                    pr_item_id=pr.items[0].id,
                    qty=Decimal("100"),
                    fulfillment_type="equivalent",
                )
            ],
        )
    assert exc.value.status_code == 422
    assert exc.value.detail == "fulfillment.qty_exceeds_soft_limit"


async def test_convert_pr_to_po_with_specs_rejects_invalid_type(seeded_db_session):
    from app.services.purchase import PRConvertSpec

    db = seeded_db_session
    actor = await _get_user(db, "alice")
    supplier = await _get_supplier(db)
    pr = await _create_pr(db, actor, supplier.id)
    await _mark_pr_approved(db, pr)

    with pytest.raises(HTTPException) as exc:
        await purchase_svc.convert_pr_to_po_with_specs(
            db,
            actor,
            pr.id,
            [
                PRConvertSpec(
                    pr_item_id=pr.items[0].id,
                    qty=Decimal("1"),
                    fulfillment_type="bogus_type",
                )
            ],
        )
    assert exc.value.status_code == 422
    assert exc.value.detail == "fulfillment.invalid_type"


async def test_update_po_item_recomputes_amount_and_po_total(seeded_db_session):
    db = seeded_db_session
    actor = await _get_user(db, "alice")
    supplier = await _get_supplier(db)
    pr = await _create_pr(db, actor, supplier.id)
    await _mark_pr_approved(db, pr)
    pos = await purchase_svc.convert_pr_to_po(db, actor, pr.id)
    po = pos[0]
    po_item = po.items[0]
    original_amount = Decimal(str(po_item.amount))
    original_qty = Decimal(str(po_item.qty))
    original_po_total = Decimal(str(po.total_amount))

    new_unit_price = Decimal("500")
    updated = await purchase_svc.update_po_item(
        db, actor, po_item.id, unit_price=new_unit_price
    )
    assert updated.unit_price == new_unit_price
    expected_new_amount = original_qty * new_unit_price
    assert Decimal(str(updated.amount)) == expected_new_amount

    refreshed_po = await purchase_svc.get_po(db, po.id)
    delta = expected_new_amount - original_amount
    assert Decimal(str(refreshed_po.total_amount)) == original_po_total + delta


async def test_update_po_item_syncs_link_qty(seeded_db_session):
    db = seeded_db_session
    actor = await _get_user(db, "alice")
    supplier = await _get_supplier(db)
    pr = await purchase_svc.create_pr(
        db,
        actor,
        PRCreateIn(
            title="Sync link qty",
            currency="CNY",
            items=[_pr_item(1, "ItemA", "10", "100", supplier_id=supplier.id)],
        ),
    )
    await _mark_pr_approved(db, pr)
    pos = await purchase_svc.convert_pr_to_po(db, actor, pr.id)
    po_item = pos[0].items[0]
    assert po_item.fulfillment_links[0].qty_contribution == Decimal("10")

    await purchase_svc.update_po_item(db, actor, po_item.id, qty=Decimal("8"))

    breakdown = await purchase_svc.get_pr_item_fulfillment_breakdown(
        db, pr.items[0].id
    )
    assert breakdown["equivalent"] == Decimal("8")


async def test_update_po_item_rejects_qty_below_received(seeded_db_session):
    from app.models import POItem

    db = seeded_db_session
    actor = await _get_user(db, "alice")
    supplier = await _get_supplier(db)
    pr = await _create_pr(db, actor, supplier.id)
    await _mark_pr_approved(db, pr)
    pos = await purchase_svc.convert_pr_to_po(db, actor, pr.id)
    po_item = pos[0].items[0]

    raw = await db.get(POItem, po_item.id)
    assert raw is not None
    raw.qty_received = Decimal("3")
    await db.commit()

    with pytest.raises(HTTPException) as exc:
        await purchase_svc.update_po_item(db, actor, po_item.id, qty=Decimal("2"))
    assert exc.value.status_code == 409
    assert exc.value.detail == "po_item.qty_below_received"


async def test_delete_po_item_recomputes_po_total(seeded_db_session):
    db = seeded_db_session
    actor = await _get_user(db, "alice")
    supplier = await _get_supplier(db)
    pr = await purchase_svc.create_pr(
        db,
        actor,
        PRCreateIn(
            title="Delete one line",
            currency="CNY",
            items=[
                _pr_item(1, "ItemA", "1", "100", supplier_id=supplier.id),
                _pr_item(2, "ItemB", "2", "50", supplier_id=supplier.id),
            ],
        ),
    )
    await _mark_pr_approved(db, pr)
    pos = await purchase_svc.convert_pr_to_po(db, actor, pr.id)
    po = pos[0]
    po_id = po.id
    original_total = Decimal(str(po.total_amount))
    item_to_delete = po.items[1]
    deleted_amount = Decimal(str(item_to_delete.amount))
    item_to_delete_id = item_to_delete.id

    await purchase_svc.delete_po_item(db, actor, item_to_delete_id)

    db.expire_all()
    refreshed_po = await purchase_svc.get_po(db, po_id)
    assert Decimal(str(refreshed_po.total_amount)) == original_total - deleted_amount
    assert len(refreshed_po.items) == 1


async def test_delete_po_item_blocked_by_shipment(seeded_db_session):
    from app.models import Shipment, ShipmentItem, ShipmentStatus

    db = seeded_db_session
    actor = await _get_user(db, "alice")
    supplier = await _get_supplier(db)
    pr = await _create_pr(db, actor, supplier.id)
    await _mark_pr_approved(db, pr)
    pos = await purchase_svc.convert_pr_to_po(db, actor, pr.id)
    po_item = pos[0].items[0]

    sh = Shipment(
        shipment_number="SH-T-1",
        po_id=pos[0].id,
        status=ShipmentStatus.ARRIVED.value,
    )
    db.add(sh)
    await db.flush()
    db.add(
        ShipmentItem(
            shipment_id=sh.id,
            po_item_id=po_item.id,
            line_no=1,
            item_name=po_item.item_name,
            qty_shipped=Decimal("1"),
            unit_price=po_item.unit_price,
        )
    )
    await db.commit()

    with pytest.raises(HTTPException) as exc:
        await purchase_svc.delete_po_item(db, actor, po_item.id)
    assert exc.value.status_code == 409
    assert exc.value.detail == "po_item.cannot_delete_has_shipments"


async def test_convert_with_specs_uses_custom_unit_price(seeded_db_session):
    from app.services.purchase import PRConvertSpec

    db = seeded_db_session
    actor = await _get_user(db, "alice")
    supplier = await _get_supplier(db)
    pr = await purchase_svc.create_pr(
        db,
        actor,
        PRCreateIn(
            title="Downgrade with custom price",
            currency="CNY",
            items=[_pr_item(1, "Server X", "10", "1000", supplier_id=supplier.id)],
        ),
    )
    await _mark_pr_approved(db, pr)

    pos = await purchase_svc.convert_pr_to_po_with_specs(
        db,
        actor,
        pr.id,
        [
            PRConvertSpec(
                pr_item_id=pr.items[0].id,
                qty=Decimal("10"),
                fulfillment_type="downgraded",
                deviation_note="missing A part",
                unit_price=Decimal("700"),
            )
        ],
    )
    assert pos[0].items[0].unit_price == Decimal("700")
    assert pos[0].items[0].amount == Decimal("7000.0000")
    assert pos[0].total_amount == Decimal("7000.0000")


async def test_convert_with_specs_supplementary_separate_supplier(seeded_db_session):
    from app.services.purchase import PRConvertSpec

    db = seeded_db_session
    actor = await _get_user(db, "alice")
    s_main = await _get_supplier(db, "SUP-DELL")
    s_gpu = await _get_supplier(db, "SUP-LENOVO")
    pr = await purchase_svc.create_pr(
        db,
        actor,
        PRCreateIn(
            title="Server with GPU bundle",
            currency="CNY",
            items=[_pr_item(1, "Server X full-config", "64", "2681000", supplier_id=s_main.id)],
        ),
    )
    await _mark_pr_approved(db, pr)

    pos = await purchase_svc.convert_pr_to_po_with_specs(
        db,
        actor,
        pr.id,
        [
            PRConvertSpec(
                pr_item_id=pr.items[0].id,
                qty=Decimal("64"),
                fulfillment_type="downgraded",
                deviation_note="missing GPU, sourced separately",
                unit_price=Decimal("681000"),
            ),
            PRConvertSpec(
                pr_item_id=pr.items[0].id,
                qty=Decimal("1024"),
                fulfillment_type="supplementary",
                supplier_id=s_gpu.id,
                item_name="NVIDIA RTX PRO 6000 BSE",
                uom="EA",
                unit_price=Decimal("129000"),
                deviation_note="GPU sourced separately",
            ),
        ],
    )

    assert len(pos) == 2
    by_supplier = {p.supplier_id: p for p in pos}
    assert s_main.id in by_supplier
    assert s_gpu.id in by_supplier
    assert by_supplier[s_main.id].items[0].qty == Decimal("64")
    assert by_supplier[s_main.id].items[0].unit_price == Decimal("681000")
    assert by_supplier[s_gpu.id].items[0].qty == Decimal("1024")
    assert by_supplier[s_gpu.id].items[0].item_name == "NVIDIA RTX PRO 6000 BSE"
    assert by_supplier[s_gpu.id].items[0].unit_price == Decimal("129000")


async def test_convert_with_specs_supplementary_skips_soft_limit(seeded_db_session):
    from app.services.purchase import PRConvertSpec

    db = seeded_db_session
    actor = await _get_user(db, "alice")
    supplier = await _get_supplier(db)
    pr = await purchase_svc.create_pr(
        db,
        actor,
        PRCreateIn(
            title="Soft limit bypass for supplementary",
            currency="CNY",
            items=[_pr_item(1, "Server", "10", "1000", supplier_id=supplier.id)],
        ),
    )
    await _mark_pr_approved(db, pr)

    pos = await purchase_svc.convert_pr_to_po_with_specs(
        db,
        actor,
        pr.id,
        [
            PRConvertSpec(
                pr_item_id=pr.items[0].id,
                qty=Decimal("160"),
                fulfillment_type="supplementary",
                item_name="GPU",
                unit_price=Decimal("100"),
            )
        ],
    )
    assert len(pos) == 1
    assert pos[0].items[0].qty == Decimal("160")


async def test_convert_with_specs_main_plus_supplementary_groups_correctly(seeded_db_session):
    from app.services.purchase import PRConvertSpec

    db = seeded_db_session
    actor = await _get_user(db, "alice")
    s_main = await _get_supplier(db, "SUP-DELL")
    s_main2 = s_main
    s_supp = await _get_supplier(db, "SUP-LENOVO")
    pr = await purchase_svc.create_pr(
        db,
        actor,
        PRCreateIn(
            title="Mix grouping",
            currency="CNY",
            items=[_pr_item(1, "Item", "10", "100", supplier_id=s_main.id)],
        ),
    )
    await _mark_pr_approved(db, pr)
    pos = await purchase_svc.convert_pr_to_po_with_specs(
        db,
        actor,
        pr.id,
        [
            PRConvertSpec(
                pr_item_id=pr.items[0].id,
                qty=Decimal("5"),
                fulfillment_type="equivalent",
            ),
            PRConvertSpec(
                pr_item_id=pr.items[0].id,
                qty=Decimal("5"),
                fulfillment_type="downgraded",
                supplier_id=s_main2.id,
                deviation_note="cheaper variant from same supplier",
                unit_price=Decimal("80"),
            ),
            PRConvertSpec(
                pr_item_id=pr.items[0].id,
                qty=Decimal("3"),
                fulfillment_type="supplementary",
                supplier_id=s_supp.id,
                item_name="Accessory",
                unit_price=Decimal("20"),
            ),
        ],
    )
    assert len(pos) == 2
    by_supplier = {p.supplier_id: p for p in pos}
    main_po = by_supplier[s_main.id]
    supp_po = by_supplier[s_supp.id]
    assert len(main_po.items) == 2
    assert len(supp_po.items) == 1
    main_total = sum(Decimal(str(i.amount)) for i in main_po.items)
    assert main_total == Decimal("900")
    assert Decimal(str(supp_po.total_amount)) == Decimal("60")
