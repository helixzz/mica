#!/usr/bin/env python3
"""Receipt edges: partial, complete, and the over-receipt that must be refused.

    python scripts/receipt-edges.py [--base URL]

Receipts were decoupled from shipments (v1.67), so "received how much" is now a first
class question rather than a side effect of creating a shipment. Three cases matter and
none had a check:

  1. receiving less than ordered  -> partially_received
  2. receiving the rest          -> fully_received
  3. receiving more              -> 409 with ordered / projected in the message
"""

from __future__ import annotations

import argparse
import asyncio

import httpx

PW = "MicaDev2026!"
SUPPLIER = "b07eae53-f10b-444b-95c5-c9cc2ab012f7"
ITEM = "f6ab4e00-7d67-4bc8-8abb-2c49093f8961"



import asyncio

import httpx




async def main(base: str) -> None:
    async with httpx.AsyncClient(base_url=base, timeout=90) as c:
        tok = (await c.post("/api/v1/auth/login/json", json={"username": "alice", "password": PW})).json()["access_token"]
        adm = (await c.post("/api/v1/auth/login/json", json={"username": "admin", "password": PW})).json()["access_token"]
        h = {"Authorization": f"Bearer {tok}"}
        ha = {"Authorization": f"Bearer {adm}"}

        pr = (await c.post("/api/v1/purchase-requisitions", json={
            "title": f"部分收货验证 {asyncio.get_event_loop().time():.0f}",
            "currency": "CNY",
            "expected_delivery_date": "2026-11-30",
            "items": [{"line_no": 1, "item_id": ITEM, "item_name": "96GB RDIMM DDR5 6400MT/s",
                       "supplier_id": SUPPLIER, "qty": "10", "uom": "EA", "unit_price": "100.00"}],
        }, headers=h)).json()
        pr_id = pr["id"]
        await c.post(f"/api/v1/purchase-requisitions/{pr_id}/submit", headers=h)
        pend = (await c.get("/api/v1/approval/pending", headers=ha)).json()
        task = next((t for t in pend if str(t.get("biz_id")) == str(pr_id)), None)
        if task:
            await c.post(f"/api/v1/approval/tasks/{task['id']}/action",
                         json={"action": "approve", "comment": "ok"}, headers=ha)
        pos = (await c.post(f"/api/v1/purchase-requisitions/{pr_id}/convert-to-po", json={}, headers=h)).json()
        po = pos[0]
        po_id = po["id"]
        detail = (await c.get(f"/api/v1/purchase-orders/{po_id}", headers=h)).json()
        item = (detail.get("items") or [{}])[0]
        print(f"PO {po['po_number']} qty={item.get('qty')} status={detail.get('status')}")

        # 收一半
        r = await c.post(f"/api/v1/purchase-orders/{po_id}/receipts", json={
            "items": [{"po_item_id": item["id"], "qty": "4"}],
        }, headers=h)
        print("receive 4 ->", r.status_code, r.text[:120] if r.status_code >= 400 else "")

        d2 = (await c.get(f"/api/v1/purchase-orders/{po_id}", headers=h)).json()
        i2 = (d2.get("items") or [{}])[0]
        print(f"after: status={d2.get('status')} received={i2.get('qty_received')}")

        # 再收剩下的
        r = await c.post(f"/api/v1/purchase-orders/{po_id}/receipts", json={
            "items": [{"po_item_id": item["id"], "qty": "6"}],
        }, headers=h)
        print("receive 6 ->", r.status_code)
        d3 = (await c.get(f"/api/v1/purchase-orders/{po_id}", headers=h)).json()
        print(f"final: status={d3.get('status')}")

        # 超收（应该被拒）
        r = await c.post(f"/api/v1/purchase-orders/{po_id}/receipts", json={
            "items": [{"po_item_id": item["id"], "qty": "1"}],
        }, headers=h)
        print("over-receive 1 ->", r.status_code, (r.text[:120] if r.status_code >= 400 else "ACCEPTED (should be rejected)"))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8012")
    raise SystemExit(asyncio.run(main(ap.parse_args().base)))
