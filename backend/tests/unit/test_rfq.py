# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnusedCallResult=false, reportUnusedFunction=false, reportMissingTypeArgument=false

from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.models import RFQQuote, RFQStatus, Item, Supplier, User
from app.services import purchase as purchase_svc
from app.services import rfq as rfq_svc


async def _get_alice(db) -> User:
    return (await db.execute(select(User).where(User.username == "alice"))).scalar_one()


async def _get_items(db) -> list[Item]:
    return list((await db.execute(select(Item).order_by(Item.code))).scalars().all())


async def _get_suppliers(db) -> list[Supplier]:
    return list((await db.execute(select(Supplier).order_by(Supplier.code))).scalars().all())


def _patch_next_number(monkeypatch):
    async def _fake_next_number(*_args, **_kwargs) -> str:
        return f"RFQ-TEST-{uuid4().hex[:8].upper()}"

    monkeypatch.setattr(purchase_svc, "_next_number", _fake_next_number, raising=False)


async def _create_rfq(
    db,
    monkeypatch,
    user: User,
    *,
    title: str = "Test RFQ",
    items: list[dict] | None = None,
    supplier_ids: list[str] | None = None,
):
    _patch_next_number(monkeypatch)
    data = {
        "title": title,
        "items": items if items is not None else [{"item_name": "Test Item", "qty": 10, "uom": "EA"}],
        "supplier_ids": supplier_ids if supplier_ids is not None else [],
    }
    return await rfq_svc.create_rfq(db, user, data)


async def _create_sent_rfq(db, monkeypatch, user: User, supplier_ids: list[str]):
    rfq = await _create_rfq(db, monkeypatch, user, supplier_ids=supplier_ids)
    return await rfq_svc.send_rfq(db, rfq.id)


async def test_create_rfq_with_items_and_supplier_ids(seeded_db_session, monkeypatch):
    alice = await _get_alice(seeded_db_session)
    supplier = (await seeded_db_session.execute(select(Supplier))).scalars().first()
    item = (await seeded_db_session.execute(select(Item))).scalars().first()

    rfq = await _create_rfq(
        seeded_db_session,
        monkeypatch,
        alice,
        items=[
            {
                "item_id": item.id,
                "item_name": item.name,
                "specification": item.specification,
                "qty": 10,
                "uom": item.uom,
            }
        ],
        supplier_ids=[str(supplier.id)],
    )

    fetched = await rfq_svc.get_rfq(seeded_db_session, rfq.id)
    assert fetched.title == "Test RFQ"
    assert fetched.status == RFQStatus.DRAFT.value
    assert fetched.created_by_id == alice.id
    assert len(fetched.items) == 1
    assert fetched.items[0].item_id == item.id
    assert fetched.items[0].qty == Decimal("10")
    assert len(fetched.suppliers) == 1
    assert fetched.suppliers[0].supplier_id == supplier.id


async def test_get_rfq_success_returns_related_rows(seeded_db_session, monkeypatch):
    alice = await _get_alice(seeded_db_session)
    supplier = (await seeded_db_session.execute(select(Supplier))).scalars().first()
    rfq = await _create_rfq(seeded_db_session, monkeypatch, alice, supplier_ids=[str(supplier.id)])

    fetched = await rfq_svc.get_rfq(seeded_db_session, rfq.id)

    assert fetched.id == rfq.id
    assert len(fetched.items) == 1
    assert len(fetched.suppliers) == 1
    assert fetched.suppliers[0].supplier.id == supplier.id
    assert fetched.quotes == []


async def test_get_rfq_not_found_raises_404(seeded_db_session):
    with pytest.raises(HTTPException) as exc:
        await rfq_svc.get_rfq(seeded_db_session, uuid4())

    assert exc.value.status_code == 404
    assert exc.value.detail == "rfq.not_found"


async def test_send_rfq_success_changes_status(seeded_db_session, monkeypatch):
    alice = await _get_alice(seeded_db_session)
    supplier = (await seeded_db_session.execute(select(Supplier))).scalars().first()
    rfq = await _create_rfq(seeded_db_session, monkeypatch, alice, supplier_ids=[str(supplier.id)])

    sent = await rfq_svc.send_rfq(seeded_db_session, rfq.id)

    assert sent.status == RFQStatus.SENT.value


async def test_send_rfq_already_sent_raises_409(seeded_db_session, monkeypatch):
    alice = await _get_alice(seeded_db_session)
    supplier = (await seeded_db_session.execute(select(Supplier))).scalars().first()
    rfq = await _create_rfq(seeded_db_session, monkeypatch, alice, supplier_ids=[str(supplier.id)])
    await rfq_svc.send_rfq(seeded_db_session, rfq.id)

    with pytest.raises(HTTPException) as exc:
        await rfq_svc.send_rfq(seeded_db_session, rfq.id)

    assert exc.value.status_code == 409
    assert exc.value.detail == "rfq.already_sent"


async def test_send_rfq_without_items_raises_422(seeded_db_session, monkeypatch):
    alice = await _get_alice(seeded_db_session)
    supplier = (await seeded_db_session.execute(select(Supplier))).scalars().first()
    rfq = await _create_rfq(
        seeded_db_session,
        monkeypatch,
        alice,
        items=[],
        supplier_ids=[str(supplier.id)],
    )

    with pytest.raises(HTTPException) as exc:
        await rfq_svc.send_rfq(seeded_db_session, rfq.id)

    assert exc.value.status_code == 422
    assert exc.value.detail == "rfq.no_items"


async def test_send_rfq_without_suppliers_raises_422(seeded_db_session, monkeypatch):
    alice = await _get_alice(seeded_db_session)
    rfq = await _create_rfq(seeded_db_session, monkeypatch, alice, supplier_ids=[])

    with pytest.raises(HTTPException) as exc:
        await rfq_svc.send_rfq(seeded_db_session, rfq.id)

    assert exc.value.status_code == 422
    assert exc.value.detail == "rfq.no_suppliers"


async def test_add_quote_success_updates_status_from_sent_to_quoting(seeded_db_session, monkeypatch):
    alice = await _get_alice(seeded_db_session)
    supplier = (await seeded_db_session.execute(select(Supplier))).scalars().first()
    rfq = await _create_sent_rfq(seeded_db_session, monkeypatch, alice, [str(supplier.id)])
    rfq_id = rfq.id
    fetched = await rfq_svc.get_rfq(seeded_db_session, rfq.id)

    quote = await rfq_svc.add_quote(
        seeded_db_session,
        rfq.id,
        {
            "rfq_item_id": str(fetched.items[0].id),
            "supplier_id": str(supplier.id),
            "unit_price": "123.45",
            "currency": "CNY",
            "delivery_days": 7,
            "notes": "quoted",
        },
    )
    updated = await rfq_svc.get_rfq(seeded_db_session, rfq_id)
    stored_quotes = list(
        (
            await seeded_db_session.execute(select(RFQQuote).where(RFQQuote.rfq_id == rfq_id))
        )
        .scalars()
        .all()
    )

    assert quote.unit_price == Decimal("123.45")
    assert updated.status == RFQStatus.QUOTING.value
    assert len(stored_quotes) == 1
    assert stored_quotes[0].id == quote.id
    assert updated.suppliers[0].status == "quoted"
    assert updated.suppliers[0].responded_at is not None


async def test_add_quote_to_existing_quoting_rfq_succeeds(seeded_db_session, monkeypatch):
    alice = await _get_alice(seeded_db_session)
    suppliers = await _get_suppliers(seeded_db_session)
    rfq = await _create_sent_rfq(
        seeded_db_session,
        monkeypatch,
        alice,
        [str(suppliers[0].id), str(suppliers[1].id)],
    )
    rfq_id = rfq.id
    fetched = await rfq_svc.get_rfq(seeded_db_session, rfq.id)
    await rfq_svc.add_quote(
        seeded_db_session,
        rfq.id,
        {
            "rfq_item_id": str(fetched.items[0].id),
            "supplier_id": str(suppliers[0].id),
            "unit_price": "100",
        },
    )

    second = await rfq_svc.add_quote(
        seeded_db_session,
        rfq.id,
        {
            "rfq_item_id": str(fetched.items[0].id),
            "supplier_id": str(suppliers[1].id),
            "unit_price": "110",
        },
    )
    updated = await rfq_svc.get_rfq(seeded_db_session, rfq_id)
    stored_quotes = list(
        (
            await seeded_db_session.execute(select(RFQQuote).where(RFQQuote.rfq_id == rfq_id))
        )
        .scalars()
        .all()
    )

    assert second.supplier_id == suppliers[1].id
    assert updated.status == RFQStatus.QUOTING.value
    assert len(stored_quotes) == 2


async def test_add_quote_rejects_draft_rfq(seeded_db_session, monkeypatch):
    alice = await _get_alice(seeded_db_session)
    supplier = (await seeded_db_session.execute(select(Supplier))).scalars().first()
    rfq = await _create_rfq(seeded_db_session, monkeypatch, alice, supplier_ids=[str(supplier.id)])
    fetched = await rfq_svc.get_rfq(seeded_db_session, rfq.id)

    with pytest.raises(HTTPException) as exc:
        await rfq_svc.add_quote(
            seeded_db_session,
            rfq.id,
            {
                "rfq_item_id": str(fetched.items[0].id),
                "supplier_id": str(supplier.id),
                "unit_price": "120.00",
            },
        )

    assert exc.value.status_code == 409
    assert exc.value.detail == "rfq.not_accepting_quotes"


async def test_award_quote_marks_selected_quotes(seeded_db_session, monkeypatch):
    alice = await _get_alice(seeded_db_session)
    suppliers = await _get_suppliers(seeded_db_session)
    rfq = await _create_sent_rfq(
        seeded_db_session,
        monkeypatch,
        alice,
        [str(suppliers[0].id), str(suppliers[1].id)],
    )
    rfq_id = rfq.id
    fetched = await rfq_svc.get_rfq(seeded_db_session, rfq.id)
    quote1 = await rfq_svc.add_quote(
        seeded_db_session,
        rfq.id,
        {
            "rfq_item_id": str(fetched.items[0].id),
            "supplier_id": str(suppliers[0].id),
            "unit_price": "100.00",
        },
    )
    quote2 = await rfq_svc.add_quote(
        seeded_db_session,
        rfq.id,
        {
            "rfq_item_id": str(fetched.items[0].id),
            "supplier_id": str(suppliers[1].id),
            "unit_price": "95.00",
        },
    )
    quote1_id = quote1.id
    quote2_id = quote2.id
    awarded = await rfq_svc.award_quote(seeded_db_session, rfq_id, [str(quote2_id)])

    assert awarded.status == RFQStatus.AWARDED.value
    assert awarded.awarded_at is not None
    # Re-fetch quotes to check is_selected (award_quote operates on re-loaded objects)
    for q in awarded.quotes:
        if q.id == quote1_id:
            assert q.is_selected is False
        elif q.id == quote2_id:
            assert q.is_selected is True


async def test_list_rfqs_returns_created_rfqs(seeded_db_session, monkeypatch):
    alice = await _get_alice(seeded_db_session)
    suppliers = await _get_suppliers(seeded_db_session)
    first = await _create_rfq(
        seeded_db_session,
        monkeypatch,
        alice,
        title="First RFQ",
        supplier_ids=[str(suppliers[0].id)],
    )
    second = await _create_rfq(
        seeded_db_session,
        monkeypatch,
        alice,
        title="Second RFQ",
        supplier_ids=[str(suppliers[1].id)],
    )

    rows = await rfq_svc.list_rfqs(seeded_db_session, alice)

    assert len(rows) >= 2
    assert {first.id, second.id}.issubset({row.id for row in rows})


async def test_create_rfq_can_store_multiple_suppliers(seeded_db_session, monkeypatch):
    alice = await _get_alice(seeded_db_session)
    suppliers = await _get_suppliers(seeded_db_session)

    rfq = await _create_rfq(
        seeded_db_session,
        monkeypatch,
        alice,
        supplier_ids=[str(suppliers[0].id), str(suppliers[1].id)],
    )
    fetched = await rfq_svc.get_rfq(seeded_db_session, rfq.id)

    assert len(fetched.suppliers) == 2
    assert {row.supplier_id for row in fetched.suppliers} == {suppliers[0].id, suppliers[1].id}
