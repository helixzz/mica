# 备份与恢复

## 自动备份

建议使用定时任务：

```bash
0 2 * * * cd /path/to/mica/deploy && ./scripts/backup.sh >> /var/log/mica-backup.log 2>&1
```

## 手动恢复

```bash
cd deploy
./scripts/restore.sh backups/mica-backup-YYYYMMDD.tar.gz --yes-i-know
```

## 操作提醒

- 恢复会覆盖当前数据库
- 恢复前先确认备份来源与时间点
- 生产环境恢复后务必做健康检查与关键流程抽检
