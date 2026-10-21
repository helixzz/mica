# Payment execute — disposable local QA surface

## Recreated for final lock-order QA (2026-09-24)
- **Final browser QA completed and resources cleaned by lead.** Both provisioning rounds are removed.
- UI: http://localhost:5178/login
- Contract: http://localhost:5178/contracts/e70d2349-565b-4d26-9716-870000000003
- Backend: http://127.0.0.1:8012, workspace source with `--reload --reload-dir /home/helixzz/mica/backend/app`; pending execution-only lock-order changes are picked up automatically.
- Frontend: workspace Vite, `VITE_API_TARGET=http://127.0.0.1:8012`, `--host localhost --port 5178 --strictPort`.
- Isolated `mica_payment_qa` on local `mica-postgres`, localhost:5432; migrations through `0055` and dev seed applied. Use the unchanged repository seed procurement-manager login; credentials are not stored here.
- Synthetic contract `QA-PAYMENT-EXECUTE`, ID `e70d2349-565b-4d26-9716-870000000003`, total CNY **15,268,000**. PO ID `e70d2349-565b-4d26-9716-870000000002`.
- Fresh installments: **20% / 3,053,600 paid; 30% / 4,580,400 planned; 50% / 7,634,000 planned**. Sole payment **`PAY-QA-PAYMENT-EXECUTE-002`**, linked to installment 1. Remaining installments have null actual amounts and payment links.
- Outbound Feishu/email, SAML and all 15 business-notification toggles disabled (18 selected toggles verified false). No scheduler; startup auto-seed false; app base URL points to QA UI.

## Evidence and next action
- Current surface: real proxied HTTP login and identity role `procurement_mgr`; contract and schedule GET successful. Paid **3,053,600**, remaining **12,214,400**, statuses **paid/planned/planned**. DB read returned exactly one payment, suffix 002.
- Login/contract HTML and ContractDetail/PaymentScheduleTab modules returned HTTP 200. Temporary seed script error diagnostics clean using its scoped backend-environment configuration.
- Lead final browser confirmation after lock-order fix: POST installment 2 returned 200; response status paid and actual amount 4,580,400. UI paid/remaining both 7,634,000; third planned. SQL verified unchanged historical 002 / 3,053,600, new confirmed 003 / 4,580,400, PO amount_paid 7,634,000. No production request.
- Previous, now-destroyed surface: lead reported browser installment 2 confirmation POST 200, unchanged 002 / 3,053,600, new 003 / 4,580,400, paid and remaining each 7,634,000, third planned. This was lead evidence, not this workstream's browser check.
- No production, pytest, application/tests/version changes, Git writes or PROJECT_STATE changes. Build not applicable to provisioning; actual source modules served successfully.

## Cleanup completed by lead
- Both PTYs below killed with cleanup=true; browser closed. Database drop and exact temporary path removal below succeeded. `ss` verified no listeners on 8012/5178. No owned runtime resources remain.
- Backend PTY **`pty_f9c74d37`**, reloader PID **1171722**; frontend PTY **`pty_85686657`**, npm PID **1171817**.
- Journal: `/tmp/opencode/payment-execute-qa-journal.md`.
- Seed script and scoped LSP config: `/tmp/opencode/payment-execute-qa/seed.py`, `/tmp/opencode/payment-execute-qa/pyrightconfig.json`. The initial flat seed path was relocated and no longer exists.
- Optional runtime media root: `/tmp/opencode/payment-execute-qa-media`.
- First stop both PTYs with `pty_kill({"id":"pty_f9c74d37","cleanup":true})` and `pty_kill({"id":"pty_85686657","cleanup":true})`, then:

```bash
docker exec mica-postgres dropdb -U mica --force mica_payment_qa
rm -rf /tmp/opencode/payment-execute-qa /tmp/opencode/payment-execute-qa-media
rm -f /tmp/opencode/payment-execute-qa-journal.md
```

Do not stop shared PostgreSQL, remove its volume or touch `mica`/`mica_test`.
