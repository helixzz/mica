# Mica Handoff — v1.19.0 → Next Session

## Current State (2026-05-20)

### Version: v1.19.0
GitHub: https://github.com/helixzz/mica/releases/tag/v1.19.0

### Completed This Session (from v1.14.1)
- **Bug fixes**: ActivityTimeline biz_type mapping, Dashboard analytics 500, Contract upload 504, ContractDetail 500
- **Multi-currency**: 8-currency selector + fmtAmount unification (backend + frontend, 47 files)
- **Proxy PR submission**: admin/procurement_mgr/it_buyer can submit PR on behalf of others
- **Suppliers responsive**: Grid.useBreakpoint() dual-render + ColumnSettings
- **MarqueeOption**: Select dropdown long-text scroll animation
- **Payment schedule UX**: Execute opens PaymentModal pre-filled instead of auto-creating
- **PO tabs unified**: All 8 tabs show counts
- **i18n cleanup**: 29 event_type translations + missing keys + raw enum rendering fixed
- **Insights module (Phase 1-3)**: 9 panels + 15 API endpoints + budgets/dashboard_configs/insight_cache tables
  - DeliveryCalendar, WorkflowKanban, BudgetGauge, SupplierScorecard, CategoryRadar
  - ApprovalBottleneck, QuarterlySummary (LLM), AnomalyWall, CashFlowForecast
- **Weekly insights digest**: scheduler job (Monday 09:00)
- **Backend notification isolation**: 10 service functions refactored to AsyncSessionLocal
- **Frontend try/catch resilience**: 17 pages protected against transient API failures
- **PR UX redesign**: Table → dual-row Card layout (PRNew + PREdit)
- **PR Detail UX**: business_reason + decision_comment in separate Cards
- **Unit tests**: 73 insights tests + daily_digest + scheduled_tasks (68.42% coverage)
- **Nginx TLS timeout**: 60s → 300s for OCR upload

### Known Issue: CI Test Ordering

**Problem**: Backend tests (test_notifications, test_system_params) intermittently fail when run after test_insights.py tests.

**Root cause**: The notification isolation refactor introduced `async with AsyncSessionLocal() as notif_db:` in service code. In production this works perfectly (isolated sessions). In tests, the `seeded_db_session` fixture uses savepoint rollback, but `AsyncSessionLocal()` creates a REAL session that commits OUTSIDE the savepoint → rows leak into the shared test DB → downstream tests see unexpected state.

**Attempted fixes (in conftest.py)**:
1. Fixture with `request.getfixturevalue` — failed due to scope mismatch (monkeypatch is function-scoped, db fixtures are session-scoped)
2. No-op mock of AsyncSessionLocal — partially works but doesn't prevent the insights tests themselves from creating real rows

**Correct fix needed**: Either:
- (A) Make `AsyncSessionLocal` a function on `db` module that can be fully replaced at import time (module-level patch before tests import service code)
- (B) Change test fixtures from `session` scope to `function` scope (major refactor, breaks existing tests)
- (C) Add a `get_notification_session()` dependency in service code that tests can override via FastAPI dependency_overrides
- (D) Use `pytest-xdist` with `--forked` to isolate test modules

**CI gate**: Currently set to `--cov-fail-under=68` (actual: 68.42%). Target: 70%.

### Production state
- mica.[REDACTED].com running v1.19.0 (all features working)
- 18 memory SKUs created on production
- Nginx proxy_read_timeout: 300s
- Scheduler: 6 cron jobs (daily_digest, approval_reminders, sla_escalation, contract_expiry, price_anomaly_scan, weekly_insights_digest)

### Pending Items
- P0: Fix CI test ordering issue (see above)
- P1: Reporting & Insights Phase 4 — weekly email template polish + user subscription UI
- P2: Budget Admin CRUD UI (table exists, API exists, no Admin panel yet)
- P3: PR form UX — apply Card layout to PREdit.tsx (PRNew done, PREdit partially done)
- P3: Restore CI coverage to 70%
