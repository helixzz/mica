# 管理员指南

本章面向**系统管理员**——负责部署、配置和维护 Mica 系统的人员。普通业务用户无需阅读本章。

---

## 部署与启动

### 环境要求

- Docker 24+ 和 Docker Compose v2
- 至少 2GB 空闲内存
- 端口 8900（Web 入口）可用

### 首次启动

```bash
cd deploy
./scripts/dev-up.sh
```

约 60-120 秒后系统就绪。访问 `http://<服务器地址>:8900`。

### 运维脚本

| 脚本 | 功能 |
|:---|:---|
| `./scripts/health.sh` | 一键健康检查 |
| `./scripts/backup.sh` | 备份数据库和文件 |
| `./scripts/restore.sh <归档文件>` | 从备份恢复（需确认） |
| `./scripts/upgrade.sh` | 升级：自动备份 → 构建 → 迁移 → 健康检查（失败自动回滚） |
| `./scripts/logs.sh backend` | 查看容器日志 |

---

## 系统管理控制台

以管理员账号登录后，左侧导航栏最下方有 **系统管理**。

### 系统参数

可在线编辑的运行时配置，无需改代码或重启服务：

- 审批金额阈值
- JWT 令牌有效期
- SKU 基准价窗口天数
- 合同到期提醒天数
- 上传文件大小限制
- 付款到期默认天数
- 等共 15+ 项

### 分类管理

维护三个分类维度，所有采购申请和物料都会引用：

| 维度 | 说明 | 示例 |
|:---|:---|:---|
| **成本中心** | 费用归属单位 | IT 部、行政部、产品部 |
| **开支类型** | 资本性 vs 运营性 | CapEx、OpEx |
| **采购种类** | 2 级层级分类 | 服务器配件 → 内存 / SSD / CPU |

### LLM 模型配置

Mica 支持接入 AI 大语言模型（用于表单润色、发票识别等）。在 **LLM 模型** Tab 可以：

1. 添加 OpenAI 兼容的第三方服务（DeepSeek / GLM / Kimi / 通义等）
2. 填写 Provider（`openai`）、Model String（如 `zai-org/glm-4.7`）、API Base 和 Key
3. 点击 **测试连接** 验证配置
4. 在 **AI 场景路由** Tab 将具体功能（表单润色、SKU 推荐）绑定到模型

!!! warning "Reasoning 模型注意"
    GLM 4.7 等推理模型会用大量 token 在"思考"上。如果 AI 返回空内容，请在路由配置中把 `max_tokens` 调高到 2000 以上。

### 用户管理

管理系统用户的角色分配和账号状态。

### 审计日志

所有关键操作（创建、审批、付款、删除）的完整记录，不可篡改，用于合规审计。

---

## 权限架构

Mica 使用三层权限控制：

1. **角色级**：不同角色看到不同的菜单和功能按钮
2. **字段级**：同一条记录中，不同角色可见的字段不同（由 Cerbos 策略引擎控制）
3. **行级**：用户只能看到自己部门/公司的数据

权限策略文件位于 `deploy/cerbos-policies/`，修改后 Cerbos 容器自动热加载，无需重启。

---

## 数据备份与恢复

### 自动备份

建议配置 crontab 定时备份：

```bash
# 每天凌晨 2 点备份
0 2 * * * cd /path/to/mica/deploy && ./scripts/backup.sh >> /var/log/mica-backup.log 2>&1
```

### 手动恢复

```bash
cd deploy
./scripts/restore.sh backups/mica-backup-20260422.tar.gz --yes-i-know
```

恢复会**覆盖当前数据库**，请谨慎操作。

---

## 故障排查

| 症状 | 排查方向 |
|:---|:---|
| 登录后白屏 | 浏览器 F12 → Network，检查 `/api/v1/auth/me` 是否 200 |
| 端口被占用 | 修改 `deploy/.env` 的 `HTTP_PORT` |
| 数据库迁移失败 | `docker compose logs migrate` 查看报错 |
| AI 返回空内容 | 检查 Admin → LLM 模型 → 测试连接；调高路由的 max_tokens |
| 通知不推送 | 检查 Admin → 系统参数 → 通知相关配置是否启用 |

---

## 版本升级

```bash
cd deploy
./scripts/upgrade.sh
```

升级脚本会自动：备份当前数据 → 拉取新镜像 → 运行数据库迁移 → 健康检查。如果任何步骤失败，自动回滚到升级前状态。
