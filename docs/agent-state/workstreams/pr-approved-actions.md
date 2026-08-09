# Approved PR Actions

## Objective

Add a safe disposition path for approved Purchase Requisitions that no longer need fulfillment.

## Locked policy

- An approved PR may be cancelled only when it has no PurchaseOrder rows.
- The PR requester may cancel their own approved PR.
- `admin`, `procurement_mgr`, and `it_buyer` may cancel any visible approved PR.
- `dept_manager`, `finance_auditor`, and non-owner requesters may not cancel it.
- Approved PRs remain non-deletable. Cancellation moves the PR to `cancelled`; existing delete behavior then allows cleanup.
- `partially_converted` and `converted` PRs cannot be cancelled.
- Approved-to-returned is not part of this change.

## Confirmed facts

- `PRStatus.CANCELLED` exists and is recognized by delete/UI status logic, but has no producer.
- Current backend returns 409 for approved delete and approved return.
- User manuals document `approved → cancelled` for special cases.
- Approved PRs without POs have no structural downstream fulfillment records; PRs with POs must be reversed from the PO layer.

## Outcome

Implementation and verification are complete. Ready for v1.51.0 release.

## Implementation state

- Added `PRCancelIn` and `POST /purchase-requisitions/{id}/cancel`.
- Added `cancel_pr`: approved-only, requester owner or admin/procurement_mgr/it_buyer, blocked when any PO exists, audited as `pr.cancelled`.
- Added frontend `Cancel PR` danger action gated by successful downstream load and zero POs.
- Added responsive wrapping for the PR header action group.
- Added zh/en i18n and updated user manual state diagrams/policy.

## Verification

- Backend full suite: 671 passed, 12 skipped, 1 xfailed, 1 xpassed.
- Frontend: type-check and build pass; 65 tests passed; i18n parity clean.
- Browser E2E: approved PR without POs shows Cancel PR; approved PR with PO does not; cancel changes status to cancelled and exposes Delete.
- Final dual visual QA: PASS / PASS, no blocking findings.
- Temporary E2E and visual-QA PRs and screenshots were cleaned.
