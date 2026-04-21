# Mica 部署脚手架

一套生产级运维脚本，用来统一 Mica 的备份、恢复、升级、日志、健康检查。
所有脚本都从 `deploy/` 目录下调用 `docker compose`，不依赖 repo 所在绝对路径。

## 脚本一览

| 脚本 | 用途 | 示例 |
|---|---|---|
| `health.sh` | 容器+DB+API 健康报告（人读 / `--json`） | `./health.sh` / `./health.sh --json` |
| `backup.sh` | 打包 PG dump + media volume + manifest | `./backup.sh --retain 30` |
| `restore.sh` | 从 backup 归档恢复（破坏性，双重确认） | `./restore.sh backups/mica-*.tar.gz --yes-i-know` |
| `upgrade.sh` | backup → build → migrate → up → 健康检查，失败自动回滚 | `./upgrade.sh --tag v0.5.0` |
| `logs.sh` | `docker compose logs` 的便捷封装 | `./logs.sh backend --tail 50` |

既有的 `dev-up.sh` / `dev-down.sh` 保持不变。

## 依赖

- docker compose v2
- `curl`
- `tar`, `gzip`, `find`, `df`, `awk`（Linux/macOS 自带）
- 可选：`jq`（仅当你要用 `--json` 输出时更漂亮）

## 快速上手

```bash
cd /home/helixzz/mica/deploy

# 1. 看健康
./scripts/health.sh

# 2. 备份（保留 14 天，默认）
./scripts/backup.sh

# 3. 跑一次 dry-run 升级
./scripts/upgrade.sh --dry-run

# 4. 真的升级（自动先 backup，失败自动回滚）
./scripts/upgrade.sh --tag v0.5.0

# 5. 紧急回滚到昨天的备份
./scripts/restore.sh backups/mica-20260421-020000-abc1234.tar.gz --yes-i-know
```

## 命令详解

### `backup.sh`

```
backup.sh [--output-dir <path>] [--retain <days>]
```

- 调用 `pg_dump -Fc` 备份 PG
- `docker run alpine tar` 打包 `mica_media` volume
- 写 `manifest.json`（版本/git sha/时间戳/文件大小/PG 版本）
- 压缩成单个 tar.gz（文件名格式 `mica-YYYYMMDD-HHMMSS-<gitsha>-<pid>.tar.gz`）
- `tar -tzf` 验证归档
- 按 `--retain` 清理老归档

### `restore.sh`

```
restore.sh <archive> --yes-i-know [--skip-media] [--skip-confirm]
```

- `--yes-i-know` 强制要求（第一道防护）
- TTY 下还会要求输入 YES 二次确认，非交互环境用 `--skip-confirm`
- 停掉 backend/frontend/nginx，保留 postgres 运行
- `DROP DATABASE WITH (FORCE)` → `CREATE DATABASE` → `pg_restore`
- 清空 media volume → 解压 media
- 重启全部 → 等 healthy → smoke test

### `upgrade.sh`

```
upgrade.sh [--tag <version>] [--skip-backup] [--dry-run] [--no-auto-rollback]
```

流程：
1. 预检：docker compose v2、磁盘 ≥ 5G、现有容器 healthy
2. `backup.sh`（拿到归档路径供回滚用）
3. `docker compose build`
4. `docker compose stop backend frontend nginx`
5. `docker compose run --rm migrate alembic upgrade head`
6. `docker compose up -d`
7. 等 healthy + smoke test

**任何一步失败**，自动触发 `restore.sh` 回滚到步骤 2 的归档（除非 `--no-auto-rollback`）。

退出码：0=成功 / 2=预检失败 / 3=备份失败 / 4=build 失败 / 5=迁移失败 / 6=健康失败 / 7=smoke 失败 / 8=已回滚 / 9=回滚失败

日志写到 `deploy/logs/upgrade-<timestamp>.log`。

### `health.sh`

- 默认人读表格：容器状态/uptime/CPU/mem + DB size / media size / 磁盘 / alembic head / system params 数 / API 与 frontend smoke
- `--json` 输出给脚本/告警管线消费

### `logs.sh`

```
logs.sh [service] [--tail N] [--since 10m|1h] [--grep PAT] [--errors-only] [--no-follow]
```

- 不指定 service 看全部；指定 `backend|frontend|nginx|postgres|migrate` 看单个
- 默认 `--follow`，指定 `--tail` 或 `--no-follow` 会转成一次性查看
- `--errors-only` 等价于 `--grep -iE 'error|warn|critical|exception|traceback|failed'`

## Cron 示例

```cron
# 每天凌晨 2 点备份，保留 30 天
0 2 * * * cd /home/helixzz/mica/deploy && ./scripts/backup.sh --retain 30 >> /var/log/mica-backup.log 2>&1

# 每 5 分钟健康检查，JSON 供告警管线消费
*/5 * * * * cd /home/helixzz/mica/deploy && ./scripts/health.sh --json > /tmp/mica-health.json

# 每周日 3 点清理超过 30 天的 upgrade/backup 日志
0 3 * * 0 find /home/helixzz/mica/deploy/logs -name '*.log' -mtime +30 -delete
```

## 常见故障排查

### 升级中途失败、自动回滚也失败

1. 看 `deploy/logs/upgrade-<ts>.log` 找到失败点
2. `./scripts/health.sh` 看当前各容器真实状态
3. 如果 postgres 挂了，先 `docker compose up -d postgres` + `./scripts/health.sh`
4. 找到最近一个备份：`ls -lt deploy/backups/ | head -5`
5. 手动恢复：`./scripts/restore.sh deploy/backups/mica-XXXX.tar.gz --yes-i-know`

### `restore.sh` 报 "database busy"

`DROP DATABASE WITH (FORCE)` 是 PG 13+ 才支持的；如果你在旧版 PG 上：

```bash
docker compose exec postgres psql -U mica -d postgres -c \
  "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='mica' AND pid<>pg_backend_pid();"
# 然后再跑 restore.sh
```

### `health.sh` 报 degraded 但 API 能用

多数情况下是 `docker stats` 失败或 `docker inspect` 输出格式异常。直接看容器状态：

```bash
docker compose ps
docker compose logs --tail 50
```

### 磁盘满了

```bash
# 清掉所有老归档（慎用）
./scripts/backup.sh --retain 0

# 或者把归档挪到大磁盘
mv deploy/backups /mnt/bigdisk/mica-backups
ln -s /mnt/bigdisk/mica-backups deploy/backups
```

## 设计取舍

- 纯 bash + docker compose + curl，没有 Python/Node 依赖
- 脚本路径通过 `$(dirname "$(readlink -f "$0")")` 定位，整个 repo 可以随意搬家
- `.env` 自动加载（读 `POSTGRES_USER` / `POSTGRES_DB` / `HTTP_PORT` 等）
- 不往外部存储推备份——本地 tar.gz，配合 `rsync`/`rclone`/`mc mirror` 自己接到 MinIO/S3
- 备份不加密——生产环境推荐外层再套 `gpg` 或用加密的备份目的地
