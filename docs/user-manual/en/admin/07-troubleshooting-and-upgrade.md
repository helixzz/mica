# Troubleshooting and Upgrade

## Common issues

| Symptom | First things to check |
|:---|:---|
| Blank screen after login | browser network panel, `/api/v1/auth/me` response |
| Port conflict | `deploy/.env` port settings |
| Migration failure | `docker compose logs migrate` |
| Empty AI response | model connectivity, routing config, token limit |
| Missing notifications | notification-related system parameters |

## Upgrade

```bash
cd deploy
./scripts/upgrade.sh
```

The standard upgrade path performs:

1. backup
2. image refresh or build
3. database migration
4. health checks
5. rollback on failure

## Upgrade recommendations

- deploy only CI-passed release versions
- confirm backups before each upgrade
- smoke-test login, approvals, orders, invoices, and payments immediately after upgrade
