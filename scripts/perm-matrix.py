#!/usr/bin/env python3
"""Role × endpoint permission matrix, run against a local environment.

    python scripts/perm-matrix.py [--base URL] [--db-url URL]

Asserts that each role either gets through the guard or is refused with 403. A role
"gets through" when the answer is anything but 403 (404/422 mean the request reached
the handler and failed on its contents — which is what we want to prove).

Why this exists: three of the defects found in one session were permission gaps
(attachments readable by anyone, attach needing only a login, and the buttons that
still offered those actions). Doc-driven checklists missed them; a matrix does not.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from urllib.parse import urlparse

import asyncpg
import httpx

PASSWORD = "MicaDev2026!"

PROCUREMENT = {"admin", "it_buyer", "procurement_mgr"}
PAYMENT = {"admin", "it_buyer", "procurement_mgr", "finance_auditor"}
EVERYONE = {
    "admin",
    "it_buyer",
    "procurement_mgr",
    "finance_auditor",
    "dept_manager",
    "requester",
}

# (method, path, roles that must NOT get 403)
CASES: list[tuple[str, str, set[str]]] = [
    ("GET", "/api/v1/purchase-requisitions", EVERYONE),
    ("POST", "/api/v1/purchase-requisitions", EVERYONE),
    ("GET", "/api/v1/purchase-orders", EVERYONE),
    ("DELETE", "/api/v1/purchase-orders/00000000-0000-0000-0000-000000000000", {"admin"}),
    ("PATCH", "/api/v1/contracts/00000000-0000-0000-0000-000000000000", PROCUREMENT),
    (
        "POST",
        "/api/v1/contracts/00000000-0000-0000-0000-000000000000/attachments",
        PROCUREMENT,
    ),
    ("POST", "/api/v1/payments", PAYMENT),
    ("POST", "/api/v1/invoices", PAYMENT),
    ("GET", "/api/v1/admin/audit-logs", {"admin"}),
]


async def load_users(db_url: str) -> dict[str, str]:
    parsed = urlparse(db_url.replace("postgresql+asyncpg://", "postgresql://"))
    conn = await asyncpg.connect(
        host=parsed.hostname,
        port=parsed.port or 5432,
        user=parsed.username,
        password=parsed.password,
        database=parsed.path.lstrip("/"),
    )
    try:
        rows = await conn.fetch("SELECT username, role FROM users ORDER BY username")
        return {row["username"]: row["role"] for row in rows}
    finally:
        await conn.close()


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8012")
    ap.add_argument(
        "--db-url", default="postgresql://mica:mica@localhost:5432/mica_e2e"
    )
    args = ap.parse_args()

    users = await load_users(args.db_url)
    if not users:
        print("no users in the target database", file=sys.stderr)
        return 2

    mismatches = 0
    async with httpx.AsyncClient(base_url=args.base, timeout=30) as client:
        tokens: dict[str, tuple[str, str]] = {}
        for username, role in users.items():
            r = await client.post(
                "/api/v1/auth/login/json",
                json={"username": username, "password": PASSWORD},
            )
            if r.status_code == 200:
                tokens[username] = (r.json()["access_token"], role)

        for method, path, allowed in CASES:
            for _username, (token, role) in tokens.items():
                r = await client.request(
                    method, path, headers={"Authorization": f"Bearer {token}"}, json={}
                )
                should_pass = role in allowed
                passed = r.status_code != 403
                if passed != should_pass:
                    mismatches += 1
                    print(
                        f"MISMATCH {role:<15} {method:<7} {path:<62} "
                        f"{r.status_code} (expected {'pass' if should_pass else '403'})"
                    )

    print(f"checked {len(CASES)} endpoints × {len(tokens)} roles: {mismatches} mismatch(es)")
    return 1 if mismatches else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
