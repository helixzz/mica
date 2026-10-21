#!/usr/bin/env python3
"""Walk one purchase end to end against a running backend.

    python scripts/mainline-check.py [--base URL] [--supplier UUID] [--item UUID]

PR → submit → approve → convert to PO → delivery plan → shipment → receipt → payment
schedule → execute. Every step prints the real response before asserting, because
guessing response shapes has cost me four false "bugs" in one night.

This exists because of what it caught: approving from the approval centre flipped the
approval instance to approved while the PR stayed "submitted", and a submitted PR
cannot be converted. Nothing else exercised that path.
"""

from __future__ import annotations

import argparse
import asyncio

import httpx

PW = "MicaDev2026!"

DEFAULT_SUPPLIER = "b07eae53-f10b-444b-95c5-c9cc2ab012f7"
DEFAULT_ITEM = "f6ab4e00-7d67-4bc8-8abb-2c49093f8961"


def show(step: str, r: httpx.Response, keys: tuple[str, ...] = ()) -> dict:
    ok = r.status_code < 400
    body: dict = {}
    try:
        body = r.json()
    except Exception:
        pass
    extra = ""
    if keys and isinstance(body, dict):
        extra = " " + " ".join(f"{k}={body.get(k)}" for k in keys if k in body)
    print(f"{'ok  ' if ok else 'FAIL'} {step:<34} {r.status_code}{extra}")
    if not ok:
        print("       ", r.text[:220])
    return body if isinstance(body, dict) else {}


async def login(c: httpx.AsyncClient, user: str) -> dict[str, str]:
    r = await c.post("/api/v1/auth/login/json", json={"username": user, "password": PW})
    r.raise_for_status()
    return {"Authorization": f"Bearer {r.json()['access_token']}"}




def show(step: str, r: httpx.Response, keys: tuple[str, ...] = ()) -> dict:
    ok = r.status_code < 400
    body: dict = {}
    try:
        body = r.json()
    except Exception:
        pass
    extra = ""
    if keys and isinstance(body, dict):
        extra = " " + " ".join(f"{k}={body.get(k)}" for k in keys if k in body)
    print(f"{'ok  ' if ok else 'FAIL'} {step:<34} {r.status_code}{extra}")
    if not ok:
        print("       ", r.text[:220])
    return body if isinstance(body, dict) else {}


async def login(c: httpx.AsyncClient, user: str) -> dict[str, str]:
    r = await c.post("/api/v1/auth/login/json", json={"username": user, "password": PW})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def main(base: str, supplier: str, item: str) -> int:
    async with httpx.AsyncClient(base_url=base, timeout=90) as c:
        alice = await login(c, "alice")   # it_buyer
        admin = await login(c, "admin")

        # 1. 创建 PR
        pr_body = {
            "title": f"主线验证 PR {asyncio.get_event_loop().time():.0f}",
            "business_reason": "端到端主线验证",
            "currency": "CNY",
            "expected_delivery_date": "2026-11-30",
            "items": [
                {
                    "line_no": 1,
                    "item_id": item,
                    "item_name": "96GB RDIMM DDR5 6400MT/s",
                    "supplier_id": supplier,
                    "qty": "2",
                    "uom": "EA",
                    "unit_price": "150.00",
                }
            ],
        }
        pr = show("create PR", await c.post("/api/v1/purchase-requisitions", json=pr_body, headers=alice), ("pr_number", "status", "id"))
        pr_id = pr.get("id")
        if not pr_id:
            return

        # 2. 提交审批
        submitted = show("submit PR", await c.post(f"/api/v1/purchase-requisitions/{pr_id}/submit", headers=alice), ("status",))

        # 3. 找出待办的审批任务并批准（真实端点是 /approval/pending）
        pending = await c.get("/api/v1/approval/pending", headers=admin)
        rows = pending.json() if pending.status_code == 200 else []
        if not isinstance(rows, list):
            rows = (rows or {}).get("items", [])
        mine = [t for t in rows if str(t.get("biz_id")) == str(pr_id)]
        if not mine:
            pending_alice = await c.get("/api/v1/approval/pending", headers=alice)
            rows2 = pending_alice.json() if pending_alice.status_code == 200 else []
            if not isinstance(rows2, list):
                rows2 = (rows2 or {}).get("items", [])
            mine = [t for t in rows2 if str(t.get("biz_id")) == str(pr_id)]
        print(f"     pending tasks for this PR: {len(mine)}")
        for t in mine[:1]:
            show(
                "approve task",
                await c.post(
                    f"/api/v1/approval/tasks/{t['id']}/action",
                    json={"action": "approve", "comment": "主线验证批准"},
                    headers=admin,
                ),
                ("status", "current_stage"),
            )

        pr_now = show(
            "re-read PR",
            await c.get(f"/api/v1/purchase-requisitions/{pr_id}", headers=alice),
            ("status",),
        )

        # 4. 转 PO —— 端点无 body，按 PR 明细里已有的供应商转换；返回 list[POOut]
        po: dict = {}
        if pr_now.get("status") in ("approved", "partially_converted"):
            created = await c.post(
                f"/api/v1/purchase-requisitions/{pr_id}/convert-to-po",
                json={},
                headers=alice,
            )
            rows = created.json() if created.status_code < 400 else []
            po = rows[0] if isinstance(rows, list) and rows else {}
            ok = created.status_code < 400 and bool(po)
            print(
                f"{'ok  ' if ok else 'FAIL'} {'convert PR to PO':<33}"
                f" {created.status_code} po={po.get('po_number')}"
            )
            if not ok:
                print("       ", created.text[:200])
                return
        else:
            print(f"     PR status is {pr_now.get('status')!r}; cannot convert")
            return

        po_id = po.get("id")

        # 5. 交货计划 → 发货 → 收货（入口是 delivery-plans，不是直接建 shipment）
        po_items = po.get("items") or []
        if not po_items:
            detail = await c.get(f"/api/v1/purchase-orders/{po_id}", headers=alice)
            po_items = (detail.json() or {}).get("items") or []
        first = po_items[0] if po_items else {}
        item_id = first.get("item_id") or first.get("id")

        plan = show(
            "create delivery plan",
            await c.post(
                "/api/v1/delivery-plans",
                json={
                    "po_id": po_id,
                    "item_id": item_id,
                    "plan_name": "主线验证交货",
                    "planned_qty": int(float(first.get("qty") or 1)),
                    "planned_date": "2026-11-30",
                },
                headers=alice,
            ),
            ("status",),
        )
        plan_id = plan.get("id")

        # 6. 发货单（PO 级）→ 收货（PO 级，可挂到发货单）
        shipment = show(
            "create shipment",
            await c.post(
                "/api/v1/shipments",
                json={
                    "po_id": po_id,
                    "items": [
                        {
                            "po_item_id": first.get("id"),
                            "qty_shipped": first.get("qty") or "1",
                        }
                    ],
                    "carrier": "主线验证物流",
                },
                headers=alice,
            ),
            ("status",),
        )
        shipment_id = shipment.get("id")

        show(
            "record receipt",
            await c.post(
                f"/api/v1/purchase-orders/{po_id}/receipts",
                json={
                    "items": [
                        {
                            "po_item_id": first.get("id"),
                            "qty": first.get("qty") or "1",
                            "shipment_id": shipment_id,
                        }
                    ]
                },
                headers=alice,
            ),
            ("status",),
        )
        after = (await c.get(f"/api/v1/purchase-orders/{po_id}", headers=alice)).json()
        print(f"     PO after receipt: status={after.get('status')}")

        # 7. 付款计划 + 执行
        show(
            "create payment schedule",
            await c.post(
                f"/api/v1/purchase-orders/{po_id}/payment-schedule",
                json={
                    "items": [
                        {
                            "installment_no": 1,
                            "label": "主线验证全款",
                            "planned_amount": po.get("total_amount") or "100",
                            "planned_date": "2026-11-30",
                        }
                    ]
                },
                headers=alice,
            ),
        )
        sched = await c.get(f"/api/v1/purchase-orders/{po_id}/payment-schedule", headers=alice)
        items = (sched.json() or {}).get("items") or []
        planned = [i for i in items if i.get("status") == "planned"]
        print(f"     planned instalments: {len(planned)} of {len(items)}")
        if planned:
            show(
                "execute payment",
                await c.post(
                    f"/api/v1/purchase-orders/{po_id}/payment-schedule/{planned[0]['installment_no']}/execute",
                    json={"payment_method": "bank_transfer", "invoice_timing": "postpaid"},
                    headers=alice,
                ),
                ("status", "actual_amount"),
            )
            final = await c.get(f"/api/v1/purchase-orders/{po_id}", headers=alice)
            body = final.json()
            print(f"     PO final: status={body.get('status')} amount_paid={body.get('amount_paid')}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8012")
    ap.add_argument("--supplier", default=DEFAULT_SUPPLIER)
    ap.add_argument("--item", default=DEFAULT_ITEM)
    a = ap.parse_args()
    raise SystemExit(asyncio.run(main(a.base, a.supplier, a.item)))
