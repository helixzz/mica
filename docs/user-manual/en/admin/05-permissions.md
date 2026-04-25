# Permission Model

Mica enforces permissions on three layers:

1. **Role-level** — visible modules and action buttons
2. **Field-level** — which fields are visible for a given user
3. **Row-level** — which business records a user is allowed to see

## Cerbos policies

Field-level rules are evaluated through the Cerbos sidecar. Policy files live in:

`deploy/cerbos-policies/`

Cerbos can hot-reload policy changes without requiring a full application restart.

## Administration guidance

- keep role design stable and predictable
- treat finance and supplier-related fields as sensitive by default
- regression-test key workflows after permission changes
