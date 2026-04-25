# Backup and Restore

## Automated backups

Recommended cron example:

```bash
0 2 * * * cd /path/to/mica/deploy && ./scripts/backup.sh >> /var/log/mica-backup.log 2>&1
```

## Manual restore

```bash
cd deploy
./scripts/restore.sh backups/mica-backup-YYYYMMDD.tar.gz --yes-i-know
```

## Important notes

- restore will overwrite the current database state
- validate the backup source and timestamp before running it
- perform health checks and a few core business smoke tests after restore
