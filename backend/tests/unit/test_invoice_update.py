"""Correcting a recorded invoice.

Context: a purchaser filed an invoice whose date was wrong (the form defaulted to today
and never took the OCR result) and there was no way to fix it — the API had no update
route at all.
"""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.models import (
    Invoice,
    InvoiceStatus,
    PurchaseOrder,
    PurchaseRequisition,
    Supplier,
    User,
)
from app.services import flow as svc


async def _actor(db) -> User:
    user = (
        await db.execute(select(User).where(User.role == "admin").limit(1))
    ).scalar_one_or_none()
    if user is not None:
        return user
    user = User(
        username=f"inv-{uuid4().hex[:6]}",
        email=f"inv-{uuid4().hex[:6]}@example.com",
        full_name="Invoice Tester",
        role="admin",
        hashed_password="x",
    )
    db.add(user)
    await db.flush()
    return user


async def _invoice(db, actor: User) -> Invoice:
    supplier = (await db.execute(select(Supplier).limit(1))).scalar_one_or_none()
    if supplier is None:
        supplier = Supplier(code=f"SUP-{uuid4().hex[:6]}", name="测试供应商")
        db.add(supplier)
        await db.flush()

    pr = PurchaseRequisition(
        pr_number=f"PR-INV-{uuid4().hex[:6]}",
        title="发票修改测试",
        requester_id=actor.id,
        company_id=actor.company_id,
        status="approved",
        currency="CNY",
        total_amount=Decimal("1000.00"),
    )
    db.add(pr)
    await db.flush()

    po = PurchaseOrder(
        po_number=f"PO-INV-{uuid4().hex[:6]}",
        pr_id=pr.id,
        supplier_id=supplier.id,
        company_id=actor.company_id,
        status="confirmed",
        currency="CNY",
        total_amount=Decimal("1000.00"),
        amount_paid=Decimal("0"),
        created_by_id=actor.id,
    )
    db.add(po)
    await db.flush()

    invoice = Invoice(
        internal_number=f"INV-{uuid4().hex[:8]}",
        invoice_number=f"NO-{uuid4().hex[:6]}",
        supplier_id=supplier.id,
        invoice_date=date(2026, 10, 22),
        subtotal=Decimal("1000.00"),
        tax_amount=Decimal("0"),
        total_amount=Decimal("1000.00"),
        currency="CNY",
        status=InvoiceStatus.DRAFT.value,
    )
    db.add(invoice)
    await db.flush()
    return invoice


async def test_the_invoice_date_can_be_corrected(seeded_db_session):
    db = seeded_db_session
    actor = await _actor(db)
    invoice = await _invoice(db, actor)

    updated = await svc.update_invoice(db, actor, invoice.id, {"invoice_date": date(2026, 9, 15)})

    assert updated.invoice_date == date(2026, 9, 15)


async def test_amounts_are_not_editable_through_the_update_path(seeded_db_session):
    """Amounts drive the PO matching a payment already relied on."""
    db = seeded_db_session
    actor = await _actor(db)
    invoice = await _invoice(db, actor)

    with pytest.raises(HTTPException) as exc:
        await svc.update_invoice(db, actor, invoice.id, {"total_amount": Decimal("1")})

    assert exc.value.status_code == 422
    assert "field_not_editable" in str(exc.value.detail)


async def test_a_duplicate_invoice_number_is_refused(seeded_db_session):
    db = seeded_db_session
    actor = await _actor(db)
    first = await _invoice(db, actor)
    second = await _invoice(db, actor)
    # same supplier, so the number must be unique within it
    second.supplier_id = first.supplier_id
    await db.flush()

    with pytest.raises(HTTPException) as exc:
        await svc.update_invoice(db, actor, second.id, {"invoice_number": first.invoice_number})

    assert exc.value.status_code == 409
    assert "number_duplicate" in str(exc.value.detail)
