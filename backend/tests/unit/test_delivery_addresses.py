"""Unit tests for the delivery address book service.

The load-bearing property here is that a requisition holds a *snapshot*: the
three text fields are copied at save time and ``delivery_address_id`` is
provenance only, so deleting an entry must not rewrite history.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DeliveryAddress, Supplier, User
from app.schemas import (
    DeliveryAddressIn,
    DeliveryAddressUpdateIn,
    PRCreateIn,
    PRItemIn,
    PRUpdateIn,
)
from app.services import delivery_addresses as svc
from app.services import purchase as purchase_svc


async def _user(db: AsyncSession, username: str) -> User:
    return (await db.execute(select(User).where(User.username == username))).scalar_one()


async def _supplier(db: AsyncSession) -> Supplier:
    return (await db.execute(select(Supplier).where(Supplier.code == "SUP-DELL"))).scalar_one()


def _address(**over: object) -> DeliveryAddressIn:
    base: dict[str, object] = {
        "contact_name": "张伟",
        "contact_phone": "13800000000",
        "detail": "上海市浦东新区张江高科技园区 88 号 5 层机房",
    }
    base.update(over)
    return DeliveryAddressIn(**base)


def _pr_item(supplier_id: object) -> PRItemIn:
    return PRItemIn(
        line_no=1,
        item_name="Widget",
        qty=Decimal("1"),
        unit_price=Decimal("100"),
        supplier_id=supplier_id,
    )


async def _pr(db: AsyncSession, actor: User, **over: object):
    base: dict[str, object] = {
        "title": "Address book PR",
        "currency": "CNY",
        "expected_delivery_date": date(2026, 10, 1),
        "items": [_pr_item((await _supplier(db)).id)],
    }
    base.update(over)
    return await purchase_svc.create_pr(db, actor, PRCreateIn(**base))


# --------------------------------------------------------------------------- #
# Visibility
# --------------------------------------------------------------------------- #


async def test_private_entry_is_invisible_to_other_users(seeded_db_session):
    db = seeded_db_session
    alice = await _user(db, "alice")
    bob = await _user(db, "bob")

    created = await svc.create_address(db, alice, _address(label="我的地址"))

    assert created.owner_id == alice.id
    assert created.is_shared is False
    assert [a.id for a in await svc.list_addresses(db, alice)] == [created.id]
    assert await svc.list_addresses(db, bob) == []


async def test_shared_entry_is_visible_to_every_reader(seeded_db_session):
    db = seeded_db_session
    dave = await _user(db, "dave")
    alice = await _user(db, "alice")

    shared = await svc.create_address(db, dave, _address(label="张江机房", is_shared=True))

    assert shared.owner_id is None
    assert shared.is_shared is True
    assert shared.company_id == dave.company_id
    assert [a.id for a in await svc.list_addresses(db, alice)] == [shared.id]


# --------------------------------------------------------------------------- #
# Authorization
# --------------------------------------------------------------------------- #


async def test_plain_user_cannot_create_a_shared_entry(seeded_db_session):
    db = seeded_db_session
    alice = await _user(db, "alice")

    with pytest.raises(HTTPException) as exc:
        await svc.create_address(db, alice, _address(is_shared=True))

    assert exc.value.status_code == 403
    assert exc.value.detail == "address.shared_requires_role"


async def test_another_users_private_entry_is_not_even_visible(seeded_db_session):
    """A private entry 404s for outsiders rather than 403s.

    Returning "forbidden" would confirm that the id exists.
    """
    db = seeded_db_session
    alice = await _user(db, "alice")
    bob = await _user(db, "bob")
    entry = await svc.create_address(db, alice, _address())

    with pytest.raises(HTTPException) as exc:
        await svc.update_address(db, bob, entry.id, DeliveryAddressUpdateIn(detail="改地址"))

    assert exc.value.status_code == 404
    assert exc.value.detail == "address.not_found"


async def test_shared_entry_is_readable_but_not_editable_by_a_plain_user(seeded_db_session):
    db = seeded_db_session
    dave = await _user(db, "dave")
    alice = await _user(db, "alice")
    shared = await svc.create_address(db, dave, _address(is_shared=True))

    with pytest.raises(HTTPException) as exc:
        await svc.update_address(db, alice, shared.id, DeliveryAddressUpdateIn(detail="x"))

    assert exc.value.status_code == 403
    assert exc.value.detail == "address.not_owner"

    updated = await svc.update_address(
        db, dave, shared.id, DeliveryAddressUpdateIn(detail="上海市浦东新区张江 99 号")
    )
    assert updated.detail == "上海市浦东新区张江 99 号"


# --------------------------------------------------------------------------- #
# Ordering and partial update
# --------------------------------------------------------------------------- #


async def test_list_orders_by_usage_then_recency(seeded_db_session):
    db = seeded_db_session
    alice = await _user(db, "alice")
    a = await svc.create_address(db, alice, _address(label="A"))
    b = await svc.create_address(db, alice, _address(label="B"))
    c = await svc.create_address(db, alice, _address(label="C"))

    await svc.touch_usage(db, b.id)
    await svc.touch_usage(db, b.id)
    await svc.touch_usage(db, c.id)
    await db.commit()

    assert [x.label for x in await svc.list_addresses(db, alice)] == ["B", "C", "A"]
    assert [x.label for x in await svc.list_addresses(db, alice)][-1] == "A"


async def test_update_distinguishes_omitted_from_cleared(seeded_db_session):
    db = seeded_db_session
    alice = await _user(db, "alice")
    entry = await svc.create_address(db, alice, _address(label="保留我"))

    # The field is absent from the payload, so it must survive.
    kept = await svc.update_address(
        db, alice, entry.id, DeliveryAddressUpdateIn(detail="北京市海淀区中关村 1 号")
    )
    assert kept.label == "保留我"
    assert kept.detail == "北京市海淀区中关村 1 号"

    # An explicit null is a deliberate clear.
    cleared = await svc.update_address(db, alice, entry.id, DeliveryAddressUpdateIn(label=None))
    assert cleared.label is None


async def test_touch_usage_tolerates_unknown_and_missing_ids(seeded_db_session):
    db = seeded_db_session

    await svc.touch_usage(db, None)
    await svc.touch_usage(db, uuid4())


# --------------------------------------------------------------------------- #
# Snapshot semantics
# --------------------------------------------------------------------------- #


async def test_deleting_an_entry_leaves_the_requisition_snapshot_intact(seeded_db_session):
    db = seeded_db_session
    alice = await _user(db, "alice")
    entry = await svc.create_address(db, alice, _address(label="待删除"))

    pr = await _pr(
        db,
        alice,
        delivery_address=entry.detail,
        delivery_contact_name=entry.contact_name,
        delivery_contact_phone=entry.contact_phone,
        delivery_address_id=entry.id,
    )
    assert pr.delivery_address_id == entry.id

    await svc.delete_address(db, alice, entry.id)

    # ON DELETE SET NULL drops the provenance link...
    assert (await db.execute(select(DeliveryAddress).where(DeliveryAddress.id == entry.id))).first() is None
    # ...but the copied text, which is what the order is actually shipped to,
    # is untouched.
    assert pr.delivery_address == "上海市浦东新区张江高科技园区 88 号 5 层机房"
    assert pr.delivery_contact_name == "张伟"
    assert pr.delivery_contact_phone == "13800000000"


async def test_saving_a_requisition_bumps_the_picked_entry_usage(seeded_db_session):
    db = seeded_db_session
    alice = await _user(db, "alice")
    entry = await svc.create_address(db, alice, _address())
    assert entry.usage_count == 0
    assert entry.last_used_at is None

    await _pr(db, alice, delivery_address_id=entry.id)

    assert entry.usage_count == 1
    assert entry.last_used_at is not None


async def test_update_pr_can_clear_every_delivery_field(seeded_db_session):
    """The edit form sends an explicit null; it must actually persist."""
    db = seeded_db_session
    alice = await _user(db, "alice")
    pr = await _pr(
        db,
        alice,
        delivery_address="上海市浦东新区张江 88 号",
        delivery_contact_name="张伟",
        delivery_contact_phone="13800000000",
    )

    updated = await purchase_svc.update_pr(
        db,
        alice,
        pr.id,
        PRUpdateIn(
            delivery_address=None,
            delivery_contact_name=None,
            delivery_contact_phone=None,
        ),
    )

    assert updated.delivery_address is None
    assert updated.delivery_contact_name is None
    assert updated.delivery_contact_phone is None
