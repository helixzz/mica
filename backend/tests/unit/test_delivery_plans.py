# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.models import DeliveryPlan, Item, Supplier, User, UserRole
from app.schemas import DeliveryPlanCreate, DeliveryPlanUpdate, PRCreateIn, PRItemIn
from app.services import delivery_plans as dp_svc
from app.services import purchase as purchase_svc


async def _get_user(db, username: str = "alice"):
    return (await db.execute(select(User).where(User.username == username))).scalar_one()


async def _get_supplier(db):
    return (await db.execute(select(Supplier).order_by(Supplier.code).limit(1))).scalar_one()


async def _get_item(db):
    return (await db.execute(select(Item).where(Item.is_enabled.is_(True)).limit(1))).scalar_one()


async def _create_confirmed_po(db, username: str = "alice", *, title: str = "Delivery PR"):
    user = await _get_user(db, username)
    supplier = await _get_supplier(db)
    item = await _get_item(db)
    payload = PRCreateIn(
        title=title,
        business_reason="Delivery plan testing",
        currency="CNY",
        items=[
            PRItemIn(
                line_no=1,
                item_id=item.id,
                item_name=item.name,
                specification=item.specification,
                supplier_id=supplier.id,
                qty=Decimal("10"),
                uom=item.uom,
                unit_price=Decimal("25"),
            )
        ],
    )
    pr = await purchase_svc.create_pr(db, user, payload)
    pr.status = "approved"
    await db.commit()
    po = (await purchase_svc.convert_pr_to_po(db, user, pr.id))[0]
    return user, item, pr, po


def _plan_payload(po_id, item_id, *, name: str = "Initial delivery") -> DeliveryPlanCreate:
    return DeliveryPlanCreate(
        po_id=po_id,
        item_id=item_id,
        plan_name=name,
        planned_qty=5,
        planned_date=date(2026, 5, 20),
        notes="first batch",
    )


async def test_create_delivery_plan_with_valid_item(seeded_db_session):
    db = seeded_db_session
    user, item, _pr, po = await _create_confirmed_po(db)

    plan = await dp_svc.create_delivery_plan(db, _plan_payload(po.id, item.id), user.id)

    assert plan.po_id == po.id
    assert plan.item_id == item.id
    assert plan.plan_name == "Initial delivery"
    assert plan.planned_qty == 5
    assert plan.planned_date == date(2026, 5, 20)
    assert plan.created_by_id == user.id


async def test_create_delivery_plan_with_nonexistent_item_raises_400(seeded_db_session):
    db = seeded_db_session
    user, _item, _pr, po = await _create_confirmed_po(db)

    with pytest.raises(HTTPException) as exc:
        await dp_svc.create_delivery_plan(db, _plan_payload(po.id, uuid4()), user.id)

    assert exc.value.status_code == 400
    assert exc.value.detail == "item.not_found"


async def test_update_delivery_plan_changes_fields(seeded_db_session):
    db = seeded_db_session
    user, item, _pr, po = await _create_confirmed_po(db)
    plan = await dp_svc.create_delivery_plan(db, _plan_payload(po.id, item.id), user.id)

    updated = await dp_svc.update_delivery_plan(
        db,
        plan.id,
        DeliveryPlanUpdate(
            plan_name="Updated delivery",
            planned_qty=8,
            planned_date=date(2026, 6, 1),
            notes="second batch",
            status="in_progress",
        ),
    )

    assert updated.plan_name == "Updated delivery"
    assert updated.planned_qty == 8
    assert updated.planned_date == date(2026, 6, 1)
    assert updated.notes == "second batch"
    assert updated.status == "in_progress"


async def test_update_delivery_plan_nonexistent_raises_404(seeded_db_session):
    db = seeded_db_session

    with pytest.raises(HTTPException) as exc:
        await dp_svc.update_delivery_plan(db, uuid4(), DeliveryPlanUpdate(plan_name="Missing"))

    assert exc.value.status_code == 404
    assert exc.value.detail == "delivery_plan.not_found"


async def test_delete_delivery_plan_success(seeded_db_session):
    db = seeded_db_session
    user, item, _pr, po = await _create_confirmed_po(db)
    plan = await dp_svc.create_delivery_plan(db, _plan_payload(po.id, item.id), user.id)

    await dp_svc.delete_delivery_plan(db, plan.id)

    assert await db.get(DeliveryPlan, plan.id) is None


async def test_delete_delivery_plan_nonexistent_raises_404(seeded_db_session):
    db = seeded_db_session

    with pytest.raises(HTTPException) as exc:
        await dp_svc.delete_delivery_plan(db, uuid4())

    assert exc.value.status_code == 404
    assert exc.value.detail == "delivery_plan.not_found"


async def test_list_delivery_plans_returns_created_plans(seeded_db_session):
    db = seeded_db_session
    user, item, _pr, po = await _create_confirmed_po(db)
    first = await dp_svc.create_delivery_plan(
        db, _plan_payload(po.id, item.id, name="Plan A"), user.id
    )
    second = await dp_svc.create_delivery_plan(
        db, _plan_payload(po.id, item.id, name="Plan B"), user.id
    )

    plans = await dp_svc.list_delivery_plans(db)

    plan_ids = {plan.id for plan in plans}
    assert {first.id, second.id}.issubset(plan_ids)
    listed_first = next(plan for plan in plans if plan.id == first.id)
    assert listed_first.item_id == item.id
    assert listed_first.item_name == item.name
    assert listed_first.actual_qty == 0


async def test_list_delivery_plans_filters_by_po_id_and_actor_scope(seeded_db_session):
    db = seeded_db_session
    alice, alice_item, _alice_pr, alice_po = await _create_confirmed_po(
        db, "alice", title="Alice delivery"
    )
    _carol, carol_item, _carol_pr, carol_po = await _create_confirmed_po(
        db, "carol", title="Carol delivery"
    )
    alice_plan = await dp_svc.create_delivery_plan(
        db, _plan_payload(alice_po.id, alice_item.id, name="Alice scoped"), alice.id
    )
    carol_plan = await dp_svc.create_delivery_plan(
        db, _plan_payload(carol_po.id, carol_item.id, name="Carol scoped"), alice.id
    )

    po_filtered = await dp_svc.list_delivery_plans(db, po_id=alice_po.id)
    assert {plan.id for plan in po_filtered} == {alice_plan.id}

    alice.role = UserRole.REQUESTER.value
    await db.flush()
    actor_filtered = await dp_svc.list_delivery_plans(db, actor=alice)

    actor_ids = {plan.id for plan in actor_filtered}
    assert alice_plan.id in actor_ids
    assert carol_plan.id not in actor_ids


async def test_requester_sees_contract_linked_delivery_plan(seeded_db_session):
    """Regression: a contract-only delivery plan (po_id=NULL) must be visible
    to the requester whose PR produced the contract's PO.
    """
    from decimal import Decimal

    from app.services import flow as flow_svc

    db = seeded_db_session
    alice, item, _pr, po = await _create_confirmed_po(db, "alice", title="Contract DP")

    contract = await flow_svc.create_contract(
        db, alice, po.id, title="Contract for DP", total_amount=Decimal("1000")
    )

    plan = await dp_svc.create_delivery_plan(
        db,
        DeliveryPlanCreate(
            contract_id=contract.id,
            item_id=item.id,
            plan_name="Contract-linked batch",
            planned_qty=3,
            planned_date=date(2026, 6, 1),
        ),
        alice.id,
    )
    assert plan.po_id is None
    assert plan.contract_id == contract.id

    alice.role = UserRole.REQUESTER.value
    await db.flush()

    # Filtered by contract_id (as the contract detail page does)
    by_contract = await dp_svc.list_delivery_plans(db, contract_id=contract.id, actor=alice)
    assert plan.id in {p.id for p in by_contract}, (
        "requester must see contract-linked delivery plan for their own PR's contract"
    )


async def test_requester_cannot_see_others_contract_delivery_plan(seeded_db_session):
    from decimal import Decimal

    from app.services import flow as flow_svc

    db = seeded_db_session
    alice, _alice_item, _alice_pr, _alice_po = await _create_confirmed_po(
        db, "alice", title="Alice DP"
    )
    carol, carol_item, _carol_pr, carol_po = await _create_confirmed_po(
        db, "carol", title="Carol DP"
    )
    carol_contract = await flow_svc.create_contract(
        db, carol, carol_po.id, title="Carol Contract", total_amount=Decimal("500")
    )
    carol_plan = await dp_svc.create_delivery_plan(
        db,
        DeliveryPlanCreate(
            contract_id=carol_contract.id,
            item_id=carol_item.id,
            plan_name="Carol batch",
            planned_qty=2,
            planned_date=date(2026, 6, 2),
        ),
        carol.id,
    )

    alice.role = UserRole.REQUESTER.value
    await db.flush()

    visible = await dp_svc.list_delivery_plans(db, actor=alice)
    assert carol_plan.id not in {p.id for p in visible}, (
        "requester must NOT see another requester's contract delivery plan"
    )


async def test_contract_plan_actual_qty_matches_po_linked_shipment(seeded_db_session):
    """Regression: a contract-linked delivery plan (po_id=NULL) must count
    actual qty from PO-linked shipments (shipment.contract_id=NULL) belonging
    to the contract's PO. Previously actual_qty was 0 due to a po_id/contract_id
    linkage mismatch, while PO progress showed 100%.
    """
    from decimal import Decimal

    from app.services import flow as flow_svc

    db = seeded_db_session
    alice, item, _pr, po = await _create_confirmed_po(db, "alice", title="Contract actual qty")

    contract = await flow_svc.create_contract(
        db, alice, po.id, title="Contract w/ delivery", total_amount=Decimal("1000")
    )

    # Contract-linked delivery plan (po_id is NULL)
    plan = await dp_svc.create_delivery_plan(
        db,
        DeliveryPlanCreate(
            contract_id=contract.id,
            item_id=item.id,
            plan_name="一次性交货",
            planned_qty=10,
            planned_date=date(2026, 6, 1),
        ),
        alice.id,
    )
    assert plan.po_id is None

    # PO-linked shipment (shipment.contract_id is NULL), same item, fully received
    await flow_svc.create_shipment(
        db,
        alice,
        po.id,
        items_in=[
            {
                "po_item_id": po.items[0].id,
                "qty_shipped": Decimal("10"),
                "qty_received": Decimal("10"),
            }
        ],
        carrier="SF",
        tracking_number="SF-001",
        expected_date=date(2026, 6, 1),
    )

    plans = await dp_svc.list_delivery_plans(db, contract_id=contract.id)
    listed = next(p for p in plans if p.id == plan.id)
    assert listed.actual_qty == 10, (
        f"contract-linked plan must count PO-linked shipment qty; got {listed.actual_qty}"
    )
