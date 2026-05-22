# Permission Model

Mica enforces permissions on three layers:

1. **Role-level** — visible modules and action buttons
2. **Field-level** — which fields are visible for a given user
3. **Row-level** — which business records a user is allowed to see

## Cerbos policies

Field-level rules are evaluated through the Cerbos sidecar. Policy files live in:

`deploy/cerbos-policies/`

Cerbos can hot-reload policy changes without requiring a full application restart.

## Row-level access (v1.21.0+)

Row-level rules are enforced in `backend/app/core/scoping.py`:

| Tier | Roles | PR scope | Downstream records | RFQ / Invoice |
|:---|:---|:---|:---|:---|
| **Full** | admin / procurement_mgr / it_buyer / finance_auditor | All | All | All |
| **Department** | dept_manager | Own department | Linked to own department's PRs | Hidden |
| **Personal** | requester | Own only | Linked to own PRs | Hidden |

Downstream records (PO, Contract, Shipment, Payment, Invoice, DeliveryPlan) derive visibility through `entity.po_id → PO.pr_id → visible PRs`.

## Administration guidance

- keep role design stable and predictable
- treat finance and supplier-related fields as sensitive by default
- regression-test key workflows after permission changes
- `requester` is the minimum-privilege role for general business staff; assign `it_buyer` to staff who need full visibility
