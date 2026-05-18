# Mica Handoff — v1.14.1 → Next Session

## Current State (2026-05-18)

### Version: v1.14.1
GitHub: https://github.com/helixzz/mica/releases/tag/v1.14.1

### Completed This Session
- **Multi-currency UI**: 8 currency symbols (¥ $ € £ JPY KRW HKD TWD), fmtAmount auto-detects
- **Enriched daily digest**: today PO summary, upcoming payments, overdue approvals
- **Activity timeline**: all 4 detail pages (PR/PO/Contract/RFQ) have Activity tab
- **Notification events in timeline**: include_notifications=true merges notification logs
- **PO delivery plans**: now include contract-linked plans
- **PO document attachments**: upload packing lists/serial sheets/receipts
- **Contract OCR**: auto-OCR fixed (isolated session, v1.13.0), timeout increased to 120s
- **Approval notification enriched**: PR number, title, amount, stage, submitter in body
- **PR autosave fixed**: user-specific keys, empty draft filtering
- **PR delete**: frontend + backend
- **Requester notifications**: PR→PO→contract→delivery→shipment chain, 10 sites
- **AGENTS.md**: mandatory release process + E2E testing requirement
- **CHANGELOG.md**: updated through v1.14.1

### Known Limitations
1. **Contract auto-OCR**: Uses separate async session (v1.13.0). Works but may need monitoring
2. **SMTP not configured**: Email notifications fail (sent_successfully: 0)
3. **RFQ + PR ActivityTimeline tabs**: Display audit logs but notification events may show as empty if biz_type mappings don't match resource_type
4. **Dashboard analytics 500**: EXTRACT(epoch FROM ...) on PostgreSQL (pre-existing)

### Pending Items (Suggested)
- P1: SMTP configuration for email notifications
- P1: Multi-currency selector on PR/PO forms (model has currency field, UI needs dropdown)
- P2: Price anomaly auto-detection in scheduler (currently manual trigger only)
- P2: Payment schedule multi-currency display
- P3: Admin dashboard for scheduler job status
- P3: Frontend attachment UI for contracts (upload flow is API-only)