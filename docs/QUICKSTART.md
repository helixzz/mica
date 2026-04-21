# Quickstart — 3 分钟体验 Mica

## 前置要求

- Docker 24+
- Docker Compose v2
- 可访问的端口 80, 8000（若与本机其它服务冲突，改 `deploy/.env`）

## 启动

```bash
cd deploy
./scripts/dev-up.sh
```

等待约 60-120 秒（首次启动需构建镜像 + 运行迁移 + 种子数据）。脚本结束后会列出本地与局域网访问 URL。

## 访问

| 入口 | URL |
|---|---|
| 前端（本机） | <http://localhost> |
| 前端（局域网） | `http://<LAN-IP>`（同网段设备直接访问，无头服务器首选） |
| API 文档（Swagger） | `http://<HOST>/api/docs` |
| API 文档（ReDoc） | `http://<HOST>/api/redoc` |
| 健康检查 | `http://<HOST>/health` |

> **LAN 绑定说明**：`deploy/.env` 默认 `HTTP_BIND=0.0.0.0`、`BACKEND_BIND=0.0.0.0`，端口对整个网段开放；`POSTGRES_BIND=127.0.0.1` 仅本机，避免数据库对外暴露。CORS 默认 `CORS_ALLOW_ALL=true`（仅 dev）。生产前收紧。

## 测试账号

所有账号密码均为：`MicaDev2026!`

| 用户名 | 角色 | 用途 |
|---|---|---|
| `alice` | IT 采购员 | 创建采购申请 |
| `bob` | 部门负责人 | 审批 |
| `carol` | 财务审核员 | 观察财务视角（仅只读） |
| `dave` | 采购经理 | 采购视角 |
| `admin` | 管理员 | 全量权限 |

## 端到端演示流程（约 3 分钟）

1. 访问 <http://localhost>
2. 用 `alice` 登录
3. 顶部可切换 **中文 / English**，界面立即响应，刷新后保持
4. 左侧菜单选 **采购申请** → 点击 **新建**
5. 填写标题（例如"Q2 新员工笔记本采购"）
6. 下方明细：选择物料（例如 MacBook Pro 16 M4 Pro）和供应商（苹果贸易）、数量 3、单价 25000
7. 点击 **提交审批** → 浏览器回到详情页，状态变成"待审批"
8. 右上角头像 → 退出登录
9. 用 `bob` 登录 → 仪表盘看到橙色待办卡片 → 点进详情 → **批准**
10. 再用 `alice` 登录 → 采购申请详情页 → **生成采购订单**
11. 跳转到 PO 详情，看到 `PO-2026-0001`

## 停止 / 清理

```bash
cd deploy
./scripts/dev-down.sh              # 停止但保留数据
docker volume rm mica_postgres_data  # 彻底清除数据
```

## 查看日志

```bash
cd deploy
docker compose logs -f              # 全部服务
docker compose logs -f backend      # 仅后端
docker compose logs -f postgres     # 仅数据库
```

## 故障排查

- **端口被占用**：修改 `deploy/.env` 的 `HTTP_PORT`、`POSTGRES_PORT`、`BACKEND_PORT`
- **数据库迁移失败**：`docker compose logs migrate`
- **前端白屏**：打开浏览器开发者工具 → Network，检查 `/api/v1/auth/me` 是否 200

## 已知限制（v0.4）

- ADFS SAML 仅有骨架，Dev 仍用本地密码登录
- LLM 默认 mock 模式（无真实密钥时返回演示文本）；管理员可在后台配置真实模型
- 审批引擎单级，复杂 DSL 路由在 v0.5+
- 合同仅记录元数据，未引入扫描件归档（v0.5+）
- 无 OCR / PDF/Excel 生成 / 飞书集成 / SKU 行情库（按路线图逐步引入）
