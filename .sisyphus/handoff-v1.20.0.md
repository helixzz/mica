# Mica Handoff — v1.20.0 → Next Session

## Current State (2026-05-22)

### Version: v1.20.0
Production: app running on internal network (HTTPS)
GitHub: https://github.com/helixzz/mica/releases/tag/v1.20.0

### P0 — Row-Level Permissions (URGENT)

Comprehensive design document: `mica-internal/decisions/0020-row-level-permissions.md`

Problems:
1. requester can see PRs from other cost centers/departments
2. PO/RFQ/Contract/Shipment/Payment/Invoice have ZERO row-level filtering
3. PRDetail page missing cost_center/company/department display

Fix plan:
- Backend: rewrite `list_prs_for_user` + add filtering to all list endpoints
- Backend: enrich PROut schema with company_name/department_name/cost_center_name
- Frontend: display the new fields in PRDetail
- Full permission matrix documented in 0020

Key files:
- `backend/app/core/scoping.py` — current (broken) filtering logic
- `backend/app/services/purchase.py:684-697` — `list_prs_for_user`
- `backend/app/services/flow.py` — contracts/shipments/payments endpoints
- `backend/app/api/v1/flow.py` — need to pass actor to service functions
- `backend/app/schemas/__init__.py:301` — PROut needs new fields

### Completed This Session (v1.14.1 → v1.20.0)
- 17 releases (v1.15.0 → v1.20.0)
- Insights module (9 panels + full API)
- Multi-currency + formatting unification
- Proxy PR submission
- Suppliers responsive
- PR UX redesign (Card layout + business_reason blocks)
- MarqueeOption
- Payment schedule UX
- i18n cleanup (29 event types)
- Invoice OCR prompt optimization
- RFQ admin edit
- CI test infrastructure fix (AsyncSessionLocal isolation)
- Nginx TLS timeout fix (504)
- 73 insights unit tests
- Weekly insights digest scheduler

### CI Status
- 8/8 green on latest commit
- Coverage: 68% (threshold: 68%)
- Known: 8 skipped tests (broken agent-generated assertions)
