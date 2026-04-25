# Roles and Permissions

Mica uses role-based access control with additional field-level and row-level restrictions.

## Main roles

| Role | Typical responsibility |
|:---|:---|
| Requester | Submit purchase requests and track their own records |
| IT Buyer | Manage quotations, orders, contracts, receiving, and payment execution support |
| Department Manager | Review and approve requests for their department |
| Finance Auditor | Review invoices, payments, and settlement-related records |
| Procurement Manager | Oversee procurement operations and higher-level approvals |
| Administrator | Configure the system, users, parameters, and operational settings |

## Permission layers

1. **Role-level access** — decides which modules and actions are visible
2. **Field-level access** — sensitive fields can be hidden based on policy
3. **Row-level access** — users only see the records they are allowed to access

## What to keep in mind

- Seeing a page does not always mean you can edit every field.
- Some actions are intentionally restricted to finance, procurement management, or administrators.
- SSO-created accounts can still be mapped into the same permission model as local accounts.
