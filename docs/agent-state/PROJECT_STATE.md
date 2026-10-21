# Current Work

## PR/PO delivery address book
- Objective: replace the free-text delivery address on requisitions/orders with an address-book dropdown plus three structured fields (recipient, contact phone, detailed address).
- Delivered as **v1.57.0** on 2026-10-16; branch `feat/pr-delivery-address-book` merged (`aaf450f`), release commit `d7528a1`, deployed via `upgrade.sh --tag v1.57.0` (167s, migration `0060`).
- Production verified: `/health` healthy at 1.57.0, `db: true`, `cerbos: true`; both `/api/v1` and `/api/v2` `delivery-addresses` return 401 (registered); existing endpoints unaffected.
- Details, write scope and the browser-E2E evidence: `workstreams/delivery-address-book.md`.
- Not done (deliberately): field-level permission on the contact phone; the same antd deprecation + unconnected-`useForm` pair in `ItemPickerWithCreate.tsx`.
- Note for parallel work: v1.56.x saw three releases in one afternoon, and the four version files collided between two branches. Since `c7624cc` (§8) a feature branch must **not** touch them.

## Payment schedule execution HTTP 500
- Objective: fix the procurement-manager contract schedule execution failure with regression and local end-to-end evidence.
- Confirmed 2026-09-24: production execution fails at `payment_schedule.execute_schedule_item` flush with `uq_payment_records_payment_number`.
- Cause: allocation uses the number of surviving PO payment records plus one; a surviving suffix 002 with count one causes reuse of 002.
- Read-only production verification found the first installment intact and the remaining two still planned. No production payment was executed during investigation.
- Scope: shared contract/PO schedule execution numbering and transactional concurrency protection; preserve historical payment records, amounts, and links. No unrelated flow or UI changes.
- Baseline: clean local worktree, application metadata 1.51.1.
- Implementation: `bg_461d6fb8`, session `ses_f2de5b02bffeTTOSle37Co3J0Q`; result file `workstreams/payment-execute-fix.md`.
- Implementation released: only shared `execute_schedule_item` changed; four new test/helper files with 19 regressions. Four version files and dated CHANGELOG now 1.51.2.
- Lead verification after lock-order correction: full backend 693 passed, 12 skipped, 1 xfailed, 1 xpassed, coverage 71.96%; Ruff check/format pass. Frontend type-check/build pass.
- Final browser QA after lock correction: real seed procurement manager executed synthetic installment 2 via confirmation modal, HTTP 200. SQL verified historical 002 / 3,053,600 unchanged, new 003 / 4,580,400 confirmed; PO paid and UI remaining both 7,634,000. Third installment planned. Isolated database only; production unchanged. Console showed existing AntD deprecation/context warnings, no payment HTTP failure.
- Static limitations: workspace Python LSP resolves the wrong environment; environment-correct basedpyright reports existing bare-dict annotations only in untouched service functions. Config also has a pre-existing PostgresDsn assignment diagnostic. No type suppression added.
- Oracle review `bg_07eadeb6` found a P2 lock inversion against `flow.delete_payment`; corrected execution to schedule -> PO without changing flow. Two new tests reproduced actual DeadlockDetectedError before correction and pass afterwards. Follow-up Oracle verdict: resolved, no blocking introduced findings.
- Both rounds of disposable QA services/database and temporary seed artifacts have been cleaned; final ports 8012/5178 have no listeners. See `workstreams/payment-execute-qa.md`.
- User explicitly authorized commit, push, release and production deployment on 2026-09-24. Production business-record changes and real payment execution remain prohibited.
- Published and deployed: release https://github.com/helixzz/mica/releases/tag/v1.51.2, tag/production HEAD `a662921804fbf74f0532a3c91c7110554499eda7`; CI success. Production DB/media/config backup retained privately; details in `workstreams/payment-release.md`.
- Deployment encountered concurrent container replacement; publisher stopped competing mutations. Final read-only verification and independent supervisor confirmed healthy 1.51.2, DB/Cerbos true, correct release HEAD and persistent APP_VERSION=1.51.2. Lead independently repeated /health successfully. No real production payment was executed.
- Release tasks: original publisher `ses_f2d83f2bcffe6D9GHgKY0bGZbj`; read-only supervisor `bg_03322ab0` / `ses_f2d7861d2ffeFyu6An6YOXc6Eh`. Fallback duplicate was stopped. Agent-state files remain local, not published.
- Next: user may retry the intended payment through the normal UI after confirming business intent. No further production actions planned. Existing deployment scripts need a separately scoped maintenance task for bind-mount backup and safe health/upgrade behavior.
