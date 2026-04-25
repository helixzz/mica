# Deployment and Operations

## Environment requirements

- Docker 24+
- Docker Compose v2
- at least 2 GB of free memory
- an available web port (default: 8900)

## First startup

```bash
cd deploy
./scripts/dev-up.sh
```

The system is usually ready in 60-120 seconds.

## Common operations scripts

| Script | Purpose |
|:---|:---|
| `./scripts/health.sh` | health check |
| `./scripts/backup.sh` | back up database and uploaded files |
| `./scripts/restore.sh <archive>` | restore from a backup |
| `./scripts/upgrade.sh` | perform an upgrade |
| `./scripts/logs.sh backend` | inspect backend logs |

## Operational guidance

- validate changes in local or staging environments first
- keep backups available before every upgrade
- protect production `.env`, certificates, and Nginx config from unintended overwrite
