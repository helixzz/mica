# 部署与运维

## 环境要求

- Docker 24+
- Docker Compose v2
- 至少 2GB 空闲内存
- Web 入口端口可用（默认 8900）

## 首次启动

```bash
cd deploy
./scripts/dev-up.sh
```

通常 60-120 秒后系统可用。

## 常用运维脚本

| 脚本 | 用途 |
|:---|:---|
| `./scripts/health.sh` | 一键健康检查 |
| `./scripts/backup.sh` | 备份数据库与文件 |
| `./scripts/restore.sh <archive>` | 从备份恢复 |
| `./scripts/upgrade.sh` | 执行升级流程 |
| `./scripts/logs.sh backend` | 查看后端日志 |

## 运维建议

- 先在本地或测试环境验证，再发布正式版本。
- 升级前确保备份可用。
- 对生产环境的 `.env`、证书和 Nginx 配置做单独保护，不要被代码覆盖。
