# Roles and Permissions

Mica uses role-based access control with additional field-level and row-level restrictions.

## Main roles

| Role | Typical responsibility |
|:---|:---|
| Requester | Submit purchase requests and track their own records only |
| IT Buyer | Manage quotations, orders, contracts, receiving; sees all business data |
| Department Manager | Review and approve requests for their department; sees only own department data |
| Finance Auditor | Review invoices, payments, and settlement-related records; sees all (read-only) |
| Procurement Manager | Oversee procurement operations and higher-level approvals; sees all |
| Administrator | Configure the system, users, parameters, and operational settings; sees all |

## Permission layers

1. **Role-level access** — decides which modules and actions are visible
2. **Field-level access** — sensitive fields can be hidden based on Cerbos policy
3. **Row-level access** — users only see the records they are allowed to access

## Row-level visibility (v1.21.0+)

| Role | PRs | PO / Contract / Shipment / Payment / DeliveryPlan | RFQ | Invoice |
|:---|:---|:---|:---|:---|
| admin / procurement_mgr / it_buyer / finance_auditor | All | All | All | All |
| dept_manager | Own department | Linked to own department's PRs | Hidden | Hidden |
| requester | Own only | Linked to own PRs | Hidden | Hidden |

Downstream entities derive visibility via `entity.po_id → PO.pr_id → visible PRs`.

## What to keep in mind

- Seeing a page does not always mean you can edit every field.
- Some actions are intentionally restricted to finance, procurement management, or administrators.
- SSO-created accounts can still be mapped into the same permission model as local accounts.
- RFQ and Invoice modules are completely hidden from `dept_manager` and `requester` roles.
