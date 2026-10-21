#!/usr/bin/env python3
"""Smoke-check the feature surfaces that the E2E suite does not cover.

    python scripts/smoke-features.py [--base URL]

Covers search, export and notifications against a running backend. Written after
finding nothing wrong with them but four wrong assumptions in my own scratch script —
so the assertions here are calibrated against real responses, not guessed shapes.
"""

from __future__ import annotations

import argparse
import asyncio
import sys

import httpx

PASSWORD = "MicaDev2026!"


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8012")
    args = ap.parse_args()

    failures: list[str] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        print(f"{'ok  ' if ok else 'FAIL'}  {name}{(' — ' + detail) if detail else ''}")
        if not ok:
            failures.append(name)

    async with httpx.AsyncClient(base_url=args.base, timeout=60) as c:
        r = await c.post(
            "/api/v1/auth/login/json",
            json={"username": "alice", "password": PASSWORD},
        )
        if r.status_code != 200:
            print(f"cannot log in: {r.status_code}")
            return 2
        h = {"Authorization": f"Bearer {r.json()['access_token']}"}

        # search — shape: {total, by_type, top_hits}
        for q, floor in (("PO", 1), ("显示器", 1)):
            r = await c.get("/api/v1/search", params={"q": q}, headers=h)
            total = (r.json() or {}).get("total") if r.status_code == 200 else -1
            check(f"search {q!r}", total >= floor, f"total={total}")

        r = await c.get("/api/v1/search/suggest", params={"q": "PO"}, headers=h)
        check("search suggest", r.status_code == 200 and bool(r.json()))

        # export — shape: {datasets: [...]}
        r = await c.get("/api/v1/exports", headers=h)
        datasets = (r.json() or {}).get("datasets") or [] if r.status_code == 200 else []
        check("export catalog", len(datasets) > 0, f"{len(datasets)} datasets")

        if datasets:
            key = datasets[0]["key"]
            for fmt, magic in (("xlsx", b"PK"), ("csv", None)):
                r = await c.get(
                    f"/api/v1/exports/{key}", params={"format": fmt}, headers=h
                )
                ok = r.status_code == 200 and len(r.content) > 100
                if ok and magic:
                    ok = r.content.startswith(magic)
                check(f"export {key} {fmt}", ok, f"{len(r.content)}B")

        # notifications — the read flag is read_at, not is_read
        r = await c.get("/api/v1/notifications", headers=h)
        items = (r.json() or {}).get("items") or [] if r.status_code == 200 else []
        check("notification list", r.status_code == 200 and isinstance(items, list))
        if items:
            check("notification fields", "read_at" in items[0], ",".join(sorted(items[0])))

        r = await c.get("/api/v1/notifications/unread-count", headers=h)
        unread = (r.json() or {}).get("total") if r.status_code == 200 else None
        check("unread count", isinstance(unread, int), f"total={unread}")

        if items:
            r = await c.post(
                "/api/v1/notifications/mark-read",
                headers=h,
                json={"ids": [items[0]["id"]]},
            )
            check("mark one read", r.status_code == 200, f"updated={(r.json() or {}).get('updated')}")

        r = await c.get("/api/v1/notifications/subscriptions", headers=h)
        check("subscriptions", r.status_code == 200 and isinstance(r.json(), list))

    print(f"\n{len(failures)} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
