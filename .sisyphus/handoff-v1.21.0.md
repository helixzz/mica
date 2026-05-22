# Mica Handoff — v1.21.0 → Next Session

## Current State (2026-05-22)

### Version: v1.21.0
Production: app running on internal network (HTTPS)
GitHub: https://github.com/helixzz/mica/releases/tag/v1.21.0

### Completed This Session (v1.20.0 → v1.21.0)

**Row-Level Permissions Hardening** — implemented [decision 0020](../mica-internal/decisions/0020-row-level-permissions.md) in full.

Key changes:
- `backend/app/core/scoping.py` rewritten from OR-based multi-source filter → clean role-direct
- `has_full_access()` / `is_rfq_hidden()` / `visible_po_id_subquery()` new helpers
- IT_BUYER fixed: now sees ALL PRs (was incorrectly limited to own)
- requester tightened: ONLY own PRs (was OR(own, cost_center, department))
- dept_manager scoped to own department (was unfiltered for downstream entities)
- ALL downstream entities now filter: PO, Contract, Shipment, Payment, Invoice, DeliveryPlan
- RFQ hidden from requester/dept_manager (list returns [], detail returns 403)
- PROut schema enriched: company_name, department_name, cost_center_name
- PRDetail.tsx displays new fields

Tests updated: 4 unit tests reflect new permission matrix.
Final state: **525 passed, 12 skipped, 1 xfailed**.

### Deployment

⚠️ **生产部署仍需手动执行** (SSH 不在本环境):
```bash
ssh <production-host>
cd /opt/mica  # or wherever deployed
git pull
cd deploy && docker compose up -d --build
./scripts/health.sh
```

### CI Status
- Last commit: pending — push after this session
- Coverage threshold: 68%
- Known: 8 skipped tests (broken agent-generated assertions, pre-existing)

### Next Candidates (P1/P2)

| Priority | Item |
|---|---|
| 🟡 | Cerbos policies should be updated to enforce same row-level matrix (currently rely on static scoping.py — works but bypasses the policy engine for row-level decisions) |
| 🟡 | Insights / Dashboard aggregations should be re-audited — they currently use raw queries that may bypass row-level scoping (acceptable for admin/procurement_mgr roles which see all anyway, but verify if dept_manager sees Dashboard correctly) |
| 🟡 | Frontend: empty-state messaging for permission-restricted lists (e.g. "您当前的角色无法查看 RFQ" instead of just empty table) |
| 🟢 | Audit script: dump permission matrix per role for security review |

### Files Modified This Session

```
backend/app/api/v1/delivery_plans.py
backend/app/api/v1/rfq.py
backend/app/config.py
backend/app/core/scoping.py            ← full rewrite
backend/app/schemas/__init__.py        ← PROut + 3 name fields
backend/app/services/delivery_plans.py
backend/app/services/flow.py           ← 5 list functions
backend/app/services/purchase.py       ← list/get_pr + list/get_po
backend/app/services/rfq.py
backend/pyproject.toml
backend/tests/unit/test_purchase.py    ← 4 tests updated
frontend/package.json
frontend/src/api/index.ts              ← interface
frontend/src/pages/PurchaseRequisitions/PRDetail.tsx
CHANGELOG.md
README.md
```
