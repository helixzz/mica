# Quickstart — 3 分钟体验 Mica

## 前置要求

- Docker 24+
- Docker Compose v2
- 端口 `8900`（前端入口）+ `8901`（backend 直连，可关）可用。若与本机其它服务冲突，改 `deploy/.env` 中的 `HTTP_PORT` / `BACKEND_PORT`。

## 启动

```bash
cd deploy
./scripts/dev-up.sh
```

等待约 60-120 秒（首次启动需构建镜像 + 运行迁移 + 种子数据）。脚本结束后会列出本地与局域网访问 URL。

## 访问

| 入口 | URL |
|---|---|
| 前端（本机） | <http://localhost:8900> |
| 前端（局域网） | `http://<LAN-IP>:8900`（同网段设备直接访问，无头服务器首选） |
| API 文档（Swagger） | `http://<HOST>:8900/api/docs` |
| API 文档（ReDoc） | `http://<HOST>:8900/api/redoc` |
| 健康检查 | `http://<HOST>:8900/health` |

> **端口说明**：默认 8900（避开 80/443 的已有生产站点）。通过 nginx 容器反代到后端 FastAPI。若主机 80 可用，把 `deploy/.env` 的 `HTTP_PORT=80` 即可。
>
> **绑定分层**：`HTTP_BIND=0.0.0.0`（LAN 可访问）、`BACKEND_BIND=0.0.0.0`（LAN 直连 debug）、`POSTGRES_BIND=127.0.0.1`（数据库不对外）。生产部署请把所有 BIND 收紧到 `127.0.0.1` 并由外层反代/防火墙控制。CORS 默认 `CORS_ALLOW_ALL=true`（仅 dev）。

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

1. 访问 <http://localhost:8900>
2. 用 `alice` 登录
3. 顶部可切换 **中文 / English**，界面立即响应，刷新后保持
4. 右上角有**主题切换**（☀ / 🌙 / 💻 跟随系统），支持浅色+暗色两种模式
5. 左侧菜单选 **采购申请** → 点击 **新建**
6. 填写标题（例如"Q2 新员工笔记本采购"）
7. 下方明细：选择物料（例如 MacBook Pro 16 M4 Pro）和供应商（苹果贸易）、数量 3、单价 25000
8. 点击 **提交审批** → 浏览器回到详情页，状态变成"待审批"
9. 右上角头像 → 退出登录
10. 用 `bob` 登录 → Header 右上角 **🔔 通知铃铛** 会有红色未读角标 → 点开看到"新审批任务" → 点击卡片直达审批详情 → **批准**
11. 再用 `alice` 登录 → 通知铃铛会收到"审批已通过" → 采购申请详情页 → **生成采购订单**
12. 跳转到 PO 详情，点 **导出 PDF** 下载采购订单给供应商，或点 **打印**

## v0.6 功能速览

- **自动化测试 114 个**（backend 82 + frontend 32）+ GitHub Actions CI 覆盖率上传 Codecov
- **代码分割**：首屏 JS 1.5 MB → 42 KB (-97%)，16 页面按需加载
- **Dashboard 月环比趋势**：4 个 StatCard 显示 ↑/↓ 百分比变化
- **暗色模式 QA**：对比度提亮 + Playwright 截图验收
- **Cerbos 授权**：字段级权限外化到 sidecar 策略引擎（4 resource policy + graceful fallback）
- **LLM 真实接入**：OpenAI 兼容路由（支持 GLM / Kimi / DeepSeek 等任意 vendor）
- **合同付款计划**（v0.6.1）：按期管理付款 + 4 种触发条件 + 现金流预测 + 执行自动创建付款记录
- **SKU 多选折线图**（v0.6.1）：交互式 SVG 价格走势对比 + 10 色调色板
- **采购分类体系**（v0.6.2）：成本中心 / 开支类型（CapEx/OpEx） / 采购种类（2 级层级） + Admin CRUD + PR 表单下拉

## v0.5 功能速览

- **Header 全局搜索**（Cmd/Ctrl+K 聚焦）：一个输入框跨 PR / PO / 合同 / 发票 / 供应商 / 物料
- **通知中心**（Header 铃铛）：审批 / 合同到期 / 价格异常自动推送；通知中心页可批量标记已读 + 管理订阅
- **Admin 控制台**（8+ 个标签页）：系统信息 / 系统参数 / **分类管理** / LLM 模型 / AI 路由 / 用户 / AI 日志 / 审计日志
- **系统参数可编辑**：15+ 项业务阈值从 Admin → 系统参数标签页编辑，无需改代码
- **多级审批 + 代理人**：通过 `approval_rules` 配置串签；出差前设置 `approval_delegations` 临时委托
- **主数据 CRUD**：供应商 / 物料 / 公司 / 部门的增删改查（Admin 权限）+ 部门树层级
- **导出**：PO 详情页有"导出 PDF"；付款列表页有"导出 Excel"
- **打印样式**：在任何业务详情页按 Ctrl+P / ⌘P 直接打印，会自动隐藏应用外壳

## 运维脚本（v0.5 新）

```bash
cd deploy

./scripts/health.sh          # 一键健康检查（人读表格 / --json）
./scripts/backup.sh          # 备份 DB + media volume 为单个 tar.gz
./scripts/upgrade.sh         # 升级：预检 → 备份 → 构建 → 迁移 → 健康检查（失败自动回滚）
./scripts/restore.sh <archive> --yes-i-know   # 从备份恢复（双重确认）
./scripts/logs.sh backend    # 容器日志聚合查看
```

详见 [deploy/scripts/README.md](../deploy/scripts/README.md)。

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

## 已知限制（v0.6）

- ADFS SAML 仅有骨架，开发环境仍用本地密码登录
- LLM 默认 `demo-mock` 模式（无真实密钥时返回演示文本）；管理员可在 Admin 控制台配置真实模型 + API Key
- 搜索引擎当前使用 `pg_trgm + tsvector`（轻量中文分词）；更高精度的 `zhparser` 方案在 v0.7+ 规划
- 飞书集成骨架已就绪但未接通真实 App ID/Secret（v0.7 路线图）
- 批量导入（Excel → 供应商 / 物料 / 报价）在 v0.7 规划
