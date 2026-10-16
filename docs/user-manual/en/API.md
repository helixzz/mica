# API Access (Personal Access Token)

The web UI is not the only way into Mica. When a **script, an external system, or an AI agent** needs to read or write Mica data, use an **API token (Personal Access Token, "PAT")**: a long-lived credential you can revoke at any time.

This page is for the person who hands out a token. The full technical reference (endpoint contracts, fields, error codes, stability commitments) lives in the repository: [docs/API.md](https://github.com/helixzz/mica/blob/main/docs/API.md).

---

## When you need an API token

| Scenario | Example |
|---|---|
| Scheduled scripts / automation | Export the procurement ledger nightly, flag POs past their delivery date |
| External system integration | Push Mica approval results into an internal dashboard |
| AI agent | Let an agent read PRs / POs to summarize or spot anomalies |
| Personal command line | Query data with `curl` instead of opening a browser |

You do **not** need a token for everyday work in the web UI. Your login session (JWT) and a PAT go through the same permission checks: whatever you can see in the UI, the token can see too — and nothing more.

---

## Create your first token

1. Sign in to Mica
2. Open **API Tokens** in the left navigation (the URL is `/settings/api-tokens`)
3. Click **Create token** and fill in:
   - **Name**: a label for your future self, e.g. `ci-inspect-script`, `agent-pr-triage`
   - **Scopes**: read-only or read and write
   - **Expiry**: number of days; leave empty for the system default (90 days, maximum 365)
4. Create it — the page shows the full token string exactly once

### Save the plaintext immediately

The plaintext appears only in the create (or rotate) response. **Once you close the dialog it is gone forever**; the list only ever shows the prefix and status. Store it right away in a password manager, CI secret, or server environment variable.

```
mica_pat_<prefix>_<secret>
```

- The prefix (`mica_pat_xxxx`) is safe to display; it identifies the token in lists
- The secret half is the actual credential — treat it like your password
- Never paste it into chat, issues, tickets, source control, or an AI conversation. If you suspect a leak, revoke or rotate immediately

---

## Choosing scopes

| Scope | Capability | Recommendation |
|---|---|---|
| `read` | Read-only. Write operations are rejected | **Default choice.** Use it for inspection, reports, exports, AI queries |
| `write` | Read and write — everything you can do through the API | Only when writes are genuinely needed (create a PR, submit for approval, upload attachments), with a shorter expiry |

Two things worth knowing:

- A token can never exceed **your own** permissions. Even a `write` token only works inside your role and department scope.
- A set of **query-semantics POST endpoints** (search, exports, insights, AI, dashboard) still works with a read-only token — they use POST for HTTP reasons but do not change business data. A read-only token therefore covers most read scenarios.

---

## Where a token cannot go

The following are impossible for **any** token and must be done by a human in the UI. This is deliberate: it stops a credential from escalating its own privileges.

- **Admin surface** (system parameters, users and roles, audit log queries)
- **SSO and sign-in / sign-up / password endpoints** — the single exception is "who am I" (`GET /api/v1/auth/me`), usable for a liveness check
- **Creating a token more powerful than itself**: a read-only token cannot issue a write token

In addition, the **real-time notification WebSocket channel currently accepts only a web login session**, not tokens.

---

## View, rotate, revoke

The **API Tokens** page lists each token's name, prefix, scopes, expiry, last used time and IP, and whether it is expired or revoked.

| Action | When to use it |
|---|---|
| **Rotate** | Periodic rotation, or a suspected leak. Rotation issues a new secret and invalidates the old one immediately — no need to revoke first, so there is no outage window |
| **Revoke** | The script is retired, someone left, the token is no longer needed. Revocation takes effect immediately and the record stays in the audit log |
| Do nothing | The token expires on its own |

**Housekeeping**: check "last used" from time to time and revoke tokens that are idle. Every unused credential is unnecessary risk.

---

## Rate limits and auditing

- **Rate limits are per token**, default 600 requests per minute. Over the limit you get `429` with a `Retry-After` header (seconds to wait). If a script keeps hitting it, lower its concurrency first, then ask an administrator about the quota.
- **Token creation, rotation, and revocation are always written to the audit log**, so an administrator can see who issued or revoked which token and when.
- **Per-request auditing is off by default.** If a window needs a complete call trail (e.g. an audit review), ask an administrator to enable it.

---

## For administrators

- **Global token list**: administrators can see everyone's tokens, filter by user, include or exclude revoked ones, and paginate; they can also force-revoke any token (for example when someone leaves).
- **System parameters**: on the "System Parameters" page of the [System Console](admin/03-system-console.md), the `api` category controls:
  - Tokens per user (default 10)
  - Default expiry (90 days) and maximum expiry (365 days)
  - Requests per minute (600)
  - Per-request auditing (off by default)
  - The POST path allowlist that read-only tokens may still call

  Changes **take effect immediately, with no service restart**.

---

## Keep reading

- [docs/API.md](https://github.com/helixzz/mica/blob/main/docs/API.md) — full integration guide: authentication, endpoint reference, curl / Python examples, AI agent guidance, error codes and troubleshooting, stability commitments
- [ADR 0004 — API authentication: Personal Access Token](https://github.com/helixzz/mica/blob/main/docs/adr/0004-api-personal-access-tokens.md) — why it is designed this way, and which alternatives were rejected
- [System Console](admin/03-system-console.md) — system parameters UI

!!! tip "Interactive debugging"
    Open `/api/docs` (Swagger UI) in your browser, click **Authorize**, and paste the token into `Value` (**do not** type the `Bearer ` prefix yourself — Swagger adds it). You can then call every endpoint from the page.
