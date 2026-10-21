# Payment execution collision fix

- Session: `ses_f2de5b02bffeTTOSle37Co3J0Q`; task: `bg_461d6fb8`.
- Scope: only shared contract/PO `execute_schedule_item`, regression tests, this evidence file. No production access, publication, versions, frontend, lockfiles, or `flow.py` changes.
- Baseline before edits: `cd backend && ruff check app` → `All checks passed!`.
- Confirmed input from lead: surviving payment suffix `002` belongs to paid installment 1; planned installment 2 currently allocates `002` using count 1.
- Code trace: both HTTP execution routes call `execute_schedule_item`, commit, and serialize `PaymentScheduleItemOut`; `_resolve_parent` preloads schedules. Current runtime `app/db/__init__.py` uses `expire_on_commit=False`.
- Implemented fix: numeric maximum for the literal `PAY-{parent.number}-` prefix; installment lock/refresh first, then transaction PO lock/refresh for numbering/amount. This order agrees with `flow.delete_payment` and protects the shared installment across linked-PO routes. No history rewrite or exception fallback.
- Test resources: existing local `mica_test` engine fixture; isolated per-test explicit seed; concurrency cases need committed uniquely named fixture rows with targeted cleanup. No debug server, runtime monkeypatch, or production fixture.
- Red command: `.venv/bin/pytest tests/test_payment_schedule_execute.py tests/test_payment_schedule_concurrency.py --tb=line -q` → **12 failed, 2 passed, 385 warnings in 1.91s** (exit 1).
- Red evidence: both HTTP sparse-history cases raised `IntegrityError ... uq_payment_records_payment_number` for suffix `002`; surviving `001,003` reused `003`; `999,1000` produced `003` instead of `1001`; literal-prefix fixtures produced `009` instead of `008`; all four independent-session races raised the same unique violation after observed PostgreSQL lock waits. The two already-paid HTTP cases passed with 409.
- Full red output is retained by tooling: `/home/helixzz/.local/share/opencode/tool-output/tool_0d223912c001daQh6m3HgZW1nv`.
- Additional red command: `.venv/bin/pytest tests/test_payment_schedule_concurrency.py::test_execute_rejects_duplicate_when_linked_po_has_a_different_parent_lock tests/test_payment_schedule_execute.py -k 'different_parent_lock or number_case1' --tb=short -q` → **3 failed, 10 deselected, 115 warnings in 2.10s** (exit 1).
- Cross-linked-PO red: actual result `[200]`, expected `[409]`—a real duplicate payment succeeds through the second PO because the cached schedule is not refreshed after waiting. Empty numeric namespace produced `009` instead of `001`.
- Service implementation changes only `execute_schedule_item`: schedule `refresh(..., with_for_update=True)` before status check, then PO `FOR UPDATE` with `populate_existing`, exact-prefix ASCII numeric max + 1. Parent PO existence is guaranteed by resolved parent/FK; removed redundant nullable get/guard when updating its amount.
- Status: Oracle `bg_07eadeb6` lock-order correction implemented and scoped regressions green. Lead must rerun full suite/browser QA and follow-up review. No temporary runtime instrumentation was created.

## Lock-order correction — verified locally

- Confirmed code paths: `flow.delete_payment` lines 1496–1507 resets the schedule and flushes record deletion; lines 1509–1530 recompute PO amount and commit. Execution previously took PO before schedule. Only execution changed.
- H1 confirmed: a deletion transaction holding the schedule plus execution holding PO creates a cycle when deletion updates PO. PostgreSQL deadlock report below proves the old cycle after the observer's exact-PID lock wait. Reordering locks makes both cases pass.
- H2 excluded with retained refresh: execution caches a paid installment while deletion owns its row, waits, then serializes `paid` with new actual amount `7000` after deletion commits. No stale 409 occurs.
- H3 excluded for the cycle: blocker PID exactly matches the isolated deleting transaction; committed seed uses unique IDs and existing fixture cleanup. Tests were serialized with other sessions per lead. A separate cancellation/pool issue in the first harness version was fixed before final red (below).
- Artifact journal closed: permanent regression `backend/tests/test_payment_schedule_delete_concurrency.py` reuses the existing committed fixture without editing old tests. No debug files, global settings, engine patching, listeners or background processes created. `PYTHONASYNCIODEBUG=1` was command-local; sessions/locks clean up through transaction contexts. Real deletion audit rows are removed by fixture actor ID in `finally`, before the reused fixture removes its user.
- Scope remains execution-only production changes, no net service growth, no new API abstraction. Existing module size/API parameter count retained for this explicitly requested minimal reorder rather than unrelated restructuring.
- Red command before service changes: `PYTHONASYNCIODEBUG=1 .venv/bin/pytest tests/test_payment_schedule_delete_concurrency.py --tb=short -q` → **2 failed, 49 warnings in 4.04s**. Both contract/direct-PO cases failed with `asyncpg.exceptions.DeadlockDetectedError: deadlock detected`, not timeout or import failure.
- Runtime cycle example: `Process 1484264 waits for ShareLock on transaction 250635; blocked by process 1484261. Process 1484261 waits for ShareLock on transaction 250636; blocked by process 1484264.` Execution failed at `SELECT ... FROM payment_schedules ... FOR UPDATE` after the observer proved it was blocked by the deleting transaction.
- Harness refinement before final red: initial uncaught child DBAPIError cancelled the deletion connection mid-I/O, contaminating the pool (`connection is closed` on the second fixture). Tests now collect only `DBAPIError` / `HTTPException`, explicitly roll back, and assert the error collection is empty after both tasks finish. Errors are surfaced, not accepted; no production catcher/retry was added.
- Minimal correction: `backend/app/services/payment_schedule.py:295–312` now performs `_find_schedule_item`, locked `refresh`, and already-paid check before acquiring the PO lock. Changed lock-order comment explains the required agreement with deletion. **Zero new production statements**, unchanged allocation and amount update; `flow.py` diff is empty.
- New regression: two parent cases in `backend/tests/test_payment_schedule_delete_concurrency.py`. The test explicitly acquires the schedule row lock in the deleting transaction to force the scheduling point, starts actual execution, waits for its observed `pg_blocking_pids` edge, then calls actual `delete_payment`. No mock or timing-only assumption. All DB/HTTP errors fail the test after rollback; the replacement payment's ID/link/7000 amount and PO total are checked as the joint outcome.
- Green command: `PYTHONASYNCIODEBUG=1 .venv/bin/pytest tests/test_payment_schedule_delete_concurrency.py tests/test_payment_schedule_execute.py tests/test_payment_schedule_concurrency.py tests/unit/test_payment_schedule.py --tb=short -q` → **49 passed, 1 xpassed, 2313 warnings in 10.11s**. Both new cases, all original 17 regressions (same/different installments and linked PO), and the existing service suite passed. No test rerun after this first successful green verification.
- Quality command: `ruff check app tests/test_payment_schedule_delete_concurrency.py` → `All checks passed!`; `ruff format --check app/services/payment_schedule.py tests/test_payment_schedule_delete_concurrency.py` → `2 files already formatted`.
- LSP was run on both changed Python files; known backend import environment issues remain. `basedpyright --pythonpath .venv/bin/python --level error app/services/payment_schedule.py tests/test_payment_schedule_delete_concurrency.py` → **8 errors, 0 warnings, 0 notes** (warnings filtered). All eight errors are unchanged bare-`dict` annotations in untouched functions, now lines 182/199/247/386/405/412/534/556. No new test or execution-block errors; no suppressions.
- Current pure LOC: service **557** (unchanged), new regression **80**. Existing large module/public parameter list retained per explicit narrow reorder scope; new test has two fixture parameters. No one-off production helper, input boundary, variant logic, defensive check, logger, negative flag, or post-delete cleanup verification was added.
- Final read-only diff/status showed only the execution fix and new regression added to this session's starting tree, plus this evidence update; lead-owned version/changelog/PROJECT_STATE files were not changed. No git writes or production operations.
- Remaining lead gates: full suite/coverage and browser E2E must be rerun after this ordering correction; previous **691 passed / 71.95%** and browser **200/new003/history002 unchanged** are pre-correction evidence, not current verification. Follow-up Oracle review remains appropriate. No system-wide payment-concurrency guarantee is made.

## Changed paths

- `backend/app/services/payment_schedule.py`: only `execute_schedule_item` changed. The caller retains transaction ownership and locks survive until commit/rollback. Payment history is read, never renumbered/deleted by execution.
- `backend/tests/payment_execute_support.py`: typed, explicit minimal ORM fixtures (including a real `procurement_mgr`) shared by the two new test modules; no legacy global-engine monkeypatch.
- `backend/tests/test_payment_schedule_execute.py`: 12 regressions covering both authenticated HTTP execution paths and schema serialization, sole existing 002, history/link/date/amount preservation, amount override and summary/PO correctness, repeat 409, surviving 001/003 deletion gap, numeric 999/1000, literal SQL wildcard prefixes, longer/different prefixes, malformed/non-ASCII suffixes, and empty numeric namespaces.
- `backend/tests/test_payment_schedule_concurrency.py`: five real PostgreSQL races using independent transactions; same/different installments for contract and direct PO, plus the same contract installment via a separate M:N-linked PO. Queries of `pg_blocking_pids` establish overlap without timing sleeps. Cached ORM references remain alive across waits. Committed test-only fixture rows are cleaned in `finally` via targeted IDs.
- `backend/tests/test_payment_schedule_delete_concurrency.py`: two deletion/execution lock-order regressions described above.
- `docs/agent-state/workstreams/payment-execute-fix.md`: this evidence/handoff.

## Initial numbering-fix verification (superseded by the lock-order run above)

From `/home/helixzz/mica/backend`:

```text
ruff check app tests/payment_execute_support.py tests/test_payment_schedule_execute.py tests/test_payment_schedule_concurrency.py
All checks passed!

ruff format --check app/services/payment_schedule.py tests/payment_execute_support.py tests/test_payment_schedule_execute.py tests/test_payment_schedule_concurrency.py
4 files already formatted

.venv/bin/pytest tests/test_payment_schedule_execute.py tests/test_payment_schedule_concurrency.py tests/unit/test_payment_schedule.py --tb=short -q
collected 48 items
47 passed, 1 xpassed, 2257 warnings in 9.98s
```

- All **17 new tests passed**, plus the complete existing payment-schedule suite. The existing non-strict xfail `test_invoice_forecast_counts_confirmed_po_as_invoiceable` xpassed; its marker/assertion were not changed.
- Warnings are existing `datetime.utcnow()` and passlib `crypt` deprecations. Runtime: Python 3.12.3 / pytest 9.0.3.
- The first green gate attempt stopped on a new unused `AsyncSession` test import; removed it, then the above gate passed. No repeat test runs after successful green verification.
- Existing fixture initializes/migrates only `localhost:5432/mica_test`; no tests were launched concurrently with another agent, and no production or volume operation was performed.

## Static checks / remaining limitations

- Required `lsp_diagnostics` was run on all four changed Python files. Workspace LSP cannot resolve backend-venv dependencies (`fastapi`, `pytest`, `httpx`, `anyio`) and treats backend-root imports as implicit relative imports. It also reports existing unparameterized dictionaries in untouched functions.
- Independent environment-correct command:
  `basedpyright --pythonpath .venv/bin/python app/services/payment_schedule.py tests/payment_execute_support.py tests/test_payment_schedule_execute.py tests/test_payment_schedule_concurrency.py`
  → **8 errors, 62 warnings**. All eight errors are existing `reportMissingTypeArgument` on untouched service `dict` annotations (lines 182, 199, 247, 385, 404, 411, 533, 555). No diagnostic is emitted for the edited `execute_schedule_item`; new test files have no errors, only unused-result / SQL-text-inferred-Any warnings. No type suppressions or checker configuration were added.
- Scope now covers the observed same-installment deletion/execution inversion only; manual creation/update and other deletion races remain outside it. `flow.py` is unchanged. No claim of system-wide payment concurrency repair.
- Locks assume the existing PostgreSQL READ COMMITTED transaction behavior; tests use the same default. A full browser/UI pass remains the lead's task; HTTP checks here use the real FastAPI routes via the existing `client` fixture, real auth and PostgreSQL, not mocked services.

## Architectural self-review

- Change responsibility: schedule execution; original large service retained to avoid unrelated refactoring. Measured pure LOC: service 557 (pre-existing oversized module), fixture 113, HTTP/numbering tests 178, concurrency tests 208 (warning band; split if more cases are added).
- Existing Pydantic request/output boundaries retained; all new functions typed. No new variant dispatch, `Any` annotation, suppression, broad exception catch, production fallback, logger, one-off production helper, or production parameter changes.
- PO non-nullness follows the parent/FK contract. Refreshed locked state is necessary concurrency evidence, not defensive rechecking. Existing multi-argument execution API is preserved to avoid changing both callers; pytest parameters represent fixture/case injection.
- Failing-first tests distinguish the production collision, numeric parsing, same-PO allocation races, stale `amount_paid`, stale paid checks, and cross-linked-PO duplicate execution. Names remain positive; test fixture cleanup trusts deletes and does not requery them.
- Exact next action for lead: inspect the reorder/new regression, rerun full suite/coverage and local browser QA, obtain follow-up review, and report the static-check limitation. Publication/production authorization remains outside this task.
