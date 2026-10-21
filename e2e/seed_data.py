"""Build the data the Playwright specs need, in a database you can throw away.

The CI smoke database only has accounts and suppliers, so every spec that needs a
business object used to skip. This seeds the two things most specs touch: a
confirmed purchase order and an RFQ that went out and is still owed quotes.

Run it against the same DATABASE_URL the app under test uses:

    cd backend && DATABASE_URL=... python ../e2e/seed_data.py

It is idempotent: re-running reuses what already exists, so the local loop does not
pile up duplicates.
"""

from __future__ import annotations

import asyncio
import os
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select

from app.db import AsyncSessionLocal, new_uuid
from app.models import RFQ, RFQSupplier, Supplier, User
from app.schemas import PRCreateIn, PRItemIn
from app.services import purchase as purchase_svc
from app.services import rfq as rfq_svc


async def _users_and_suppliers(db):
    buyer = (await db.execute(select(User).where(User.username == "alice"))).scalar_one_or_none()
    if buyer is None:
        raise SystemExit("seed accounts missing: start the app once with AUTO_SEED_ON_STARTUP=true")
    suppliers = (await db.execute(select(Supplier).limit(2))).scalars().all()
    if not suppliers:
        raise SystemExit("no suppliers seeded")
    return buyer, suppliers


async def _confirmed_po(db, buyer, supplier):
    pr = await purchase_svc.create_pr(
        db,
        buyer,
        PRCreateIn(
            expected_delivery_date=date.today() + timedelta(days=45),
            title="E2E 采购申请",
            business_reason="Playwright seed",
            currency="CNY",
            items=[
                PRItemIn(
                    line_no=1,
                    item_name="E2E 显示器",
                    qty=Decimal("6"),
                    unit_price=Decimal("100"),
                    supplier_id=supplier.id,
                    uom="EA",
                ),
                PRItemIn(
                    line_no=2,
                    item_name="E2E 线缆",
                    qty=Decimal("4"),
                    unit_price=Decimal("50"),
                    supplier_id=supplier.id,
                    uom="EA",
                ),
            ],
        ),
    )
    pr.status = "approved"
    await db.commit()
    po = (await purchase_svc.convert_pr_to_po(db, buyer, pr.id))[0]
    print(f"PO={po.po_number} ({po.id})")
    return po


async def _sent_rfq(db, buyer, suppliers):
    existing = (
        await db.execute(select(RFQ).where(RFQ.title == "E2E 待回传询价"))
    ).scalar_one_or_none()
    if existing is not None:
        print(f"RFQ={existing.rfq_number} ({existing.id}) reused")
        return existing

    rfq = await rfq_svc.create_rfq(
        db,
        buyer,
        {
            "title": "E2E 待回传询价",
            "deadline": date.today() - timedelta(days=3),  # already late: exercises overdue
            "items": [
                {
                    "item_name": "E2E 服务器",
                    "specification": "2U / 双电源",
                    "qty": Decimal("2"),
                    "uom": "台",
                },
                {
                    "item_name": "E2E 光模块",
                    "specification": "10G SFP+",
                    "qty": Decimal("8"),
                    "uom": "个",
                },
            ],
            "supplier_ids": [supplier.id for supplier in suppliers],
        },
    )
    # create_rfq only writes the RFQ itself; invitations are added separately.
    for supplier in suppliers:
        db.add(RFQSupplier(id=new_uuid(), rfq_id=rfq.id, supplier_id=supplier.id))
    await db.flush()
    await rfq_svc.send_rfq(db, rfq.id)
    await db.commit()
    print(f"RFQ={rfq.rfq_number} ({rfq.id}) sent, awaiting quotes")
    return rfq


async def main() -> None:
    if not os.environ.get("DATABASE_URL"):
        raise SystemExit("DATABASE_URL must point at the database under test")
    async with AsyncSessionLocal() as db:
        buyer, suppliers = await _users_and_suppliers(db)
        await _confirmed_po(db, buyer, suppliers[0])
        await _sent_rfq(db, buyer, suppliers)


if __name__ == "__main__":
    asyncio.run(main())
