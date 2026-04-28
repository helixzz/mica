# AGENTS.md — Mica 开发导读

> 本文件供 AI coding assistant（Claude / Copilot / Cursor 等）和人类工程师快速理解 Mica 代码库、约定与常见操作。新 session / 新同事读这一份 + `README.md` + `docs/DEVELOPMENT.md` 即可上手。

---

## 1. 项目一分钟速览

- **Mica（觅采）** — 企业内部采购管理系统（Internal Procurement Management System）
- **规模**：单公司 < 100 员工、月 < 300 单的 IT 部门内部使用
- **License**：Apache 2.0
- **状态**：v0.9.42（2026-04-28）· [CHANGELOG.md](./CHANGELOG.md) · [Release](https://github.com/helixzz/mica/releases/tag/v0.9.39)
- **设计准则**：效率优先 > 扩展性 > 标准化管控
- **仓库**：`git@github.com:helixzz/mica.git`（main 分支）

## 2. 技术栈

| 层 | 选型 | 版本 |
|---|---|---|
| 后端语言 | Python | 3.12 |
| 后端框架 | FastAPI + SQLAlchemy 2.x (async) + Alembic | latest |
| 后端数据 | PostgreSQL + pg_trgm + tsvector | 16 (alpine) |
| 前端框架 | React + TypeScript + Vite | React 18 / TS 5 |
| 前端 UI | Ant Design 5 + Zustand + react-i18next | latest |
| 字体 | Inter（@fontsource）+ JetBrains Mono | - |
| LLM 网关 | LiteLLM SDK | - |
| PDF/Excel | reportlab + openpyxl | 4.2+ / 3.1+ |
| 部署 | Docker Compose v2 + Nginx | - |

## 3. 仓库结构

```
mica/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI 入口
│   │   ├── config.py               # Pydantic Settings（bootstrap defaults）
│   │   ├── db/__init__.py          # engine / session / Base / TimestampMixin
│   │   ├── models/__init__.py      # 所有 SQLAlchemy 模型（单文件 ~1100 行）
│   │   ├── schemas/__init__.py     # 所有 Pydantic request/response
│   │   ├── core/                   # security / authz / field_authz / i18n
│   │   ├── api/
│   │   │   ├── __init__.py         # 聚合 router
│   │   │   └── v1/                 # 所有 REST 端点，每文件一个业务域
│   │   ├── services/               # 业务逻辑层
│   │   ├── i18n/messages/          # zh-CN.json / en-US.json
│   ├── migrations/versions/        # Alembic 迁移文件（0001-0008）
│   └── pyproject.toml              # 依赖 + ruff 配置
├── frontend/
│   └── src/
│       ├── theme/                  # tokens + AntD theme + ThemeProvider
│       ├── styles/global.css       # CSS vars + print + responsive
│       ├── components/
│       │   ├── Layout/AppLayout.tsx  # 应用外壳（有 Search + Notification slot）
│       │   ├── ui/                 # PageHeader / StatCard / Section / EmptyState
│       │   ├── GlobalSearch/       # 填 AppLayout SearchSlot
│       │   ├── NotificationBell/   # 填 AppLayout NotificationSlot
│       │   └── PrintButton.tsx     # 通用打印触发器
│       ├── pages/                  # 每个业务视图一个文件/目录
│       │   ├── Dashboard.tsx       # 角色化仪表盘
│       │   ├── SearchResults.tsx   # /search 全页
│       │   ├── NotificationCenter.tsx
│       │   ├── Admin.tsx           # 7 tabs（含 admin/SystemParamsTab.tsx）
│       ├── stores/                 # Zustand stores（notification 等）
│       ├── api/                    # axios 封装 + 业务 API wrappers
│       ├── routes/index.tsx        # 路由表
│       ├── i18n/locales/           # zh-CN / en-US common.json
│       ├── auth/                   # 登录态
│       └── assets/illustrations/   # 水獭 SVG 插画
├── deploy/
│   ├── docker-compose.yml          # 定义 postgres / migrate / backend / frontend / nginx
│   ├── .env.example
│   ├── nginx/conf.d/mica.conf
│   └── scripts/                    # backup / restore / upgrade / health / logs / dev-up / dev-down
├── docs/
│   ├── QUICKSTART.md               # 3 分钟体验
│   ├── DEVELOPMENT.md              # 开发者指南
│   ├── adr/                        # 架构决策记录
│   └── user-manual/                # mkdocs 站源（已发布到 GitHub Pages）
├── scripts/                        # 开发辅助脚本
├── README.md
├── CHANGELOG.md
├── AGENTS.md                       # ← 你在这里
├── mkdocs.yml
├── LICENSE  NOTICE
└── .github/workflows/              # ci.yml + docs.yml
```

## 4. 启动与验证

```bash
cd deploy
./scripts/dev-up.sh                 # 首次 60-120 秒（构建镜像 + 迁移 + seed）
./scripts/health.sh                 # 健康检查（人读 + --json）
```

- Web: http://localhost:8900 · LAN: `http://<LAN-IP>:8900`
- 种子账号（密码全部 `MicaDev2026!`）：`admin / alice / bob / carol / dave`
- API 文档：http://localhost:8900/api/docs（Swagger）

## 5. 关键约定（必须遵守）

### 5.1 数据库迁移
- Alembic 迁移编号**严格顺序**：`0001_initial → 0002_notifications → … → 0006_schema_additions`
- 新增迁移：`docker compose exec backend alembic revision -m "add foo"` 或手写
- **凡是改动 `models/__init__.py` 增删字段，必须配套迁移**，否则 fresh deploy 会挂
- Alembic revision 值用数字字符串 `"0007"`、`down_revision` 链到前一个

### 5.2 权限
- 每个 REST endpoint 都要在签名里注入 `user: CurrentUser`（来自 `core/security.py`）
- 角色检查走 `Depends(require_roles("admin", "procurement_mgr"))`
- 字段级读权限：`core/field_authz.py` 的 `FIELD_PERMISSIONS` 字典
- 行级过滤：在 service 层显式 where 条件，依据 `user.role` 和 `user.department_id`

### 5.3 i18n
- 后端消息加到 `backend/app/i18n/messages/{zh-CN,en-US}.json`，代码里 `raise HTTPException(400, detail=t("pr.no_items", locale))`
- 前端加到 `frontend/src/i18n/locales/{zh-CN,en-US}/common.json`，组件里 `const { t } = useTranslation(); t("button.submit")`
- **不要**用硬编码中文字符串，一律走 i18n key
- CJK 全角标点在 i18n 字符串里是合法的（ruff 已忽略 RUF001/002/003）

### 5.4 系统参数（不要硬编码阈值）
- 任何可配置阈值**不要**写成常量，加到 `system_parameters` 表（见 [ADR 0003](./docs/adr/0003-system-parameters.md)）
- 代码里读：`from app.services.system_params import system_params; limit = await system_params.get_int(db, "myfeature.max_items")`
- 新增参数要写 Alembic migration（`op.bulk_insert` seed 一行）
- `config.py` 里的值是 bootstrap fallback，不是运行时真相

### 5.5 审批规则（不要绕过 DSL）
- 审批路由由 `approval_rules` 表配置（`biz_type + amount_min/max + stages`）
- 新 biz_type 走审批：在 `approval_rules` 加一行 seed，调 `services/approval.create_instance_for_pr()` 式的模板
- 审批代理人由 `approver_delegations` 自动生效，**不要**在业务代码里跳过委托检查

### 5.6 通知
- 业务事件 → `from app.services.notifications import create_notification`
- 新 category → 先在 `NotificationCategory` enum 加值，再在前端 `NotificationBell` 的 icon map 加一条
- 通知失败**不能**阻塞业务流程，用 try/except + logger.warning

### 5.7 搜索
- 新实体要加入全局搜索：加 `search_vector` 生成列（migration）+ 在 `services/search.py` 注册 entity_type
- 当前用 pg_trgm（[ADR 0002](./docs/adr/0002-search-pg-trgm-over-zhparser.md)），不要引入 zhparser

### 5.8 前端主题
- 颜色/间距/字号 → 用 tokens（`frontend/src/theme/tokens.ts`），不要硬编码 hex
- AntD 组件 → `useToken()` 获取语义 token
- 非 AntD 区域 → 用 CSS 变量 `var(--color-primary)` / `var(--space-4)` 等
- **不要**引入 Tailwind / styled-components / emotion，纯 AntD + CSS custom properties

### 5.9 日期时间
- 一律用 `datetime.UTC` 而非 `datetime.timezone.utc`（Python 3.12）
- 数据库 timestamp 列必须 `DateTime(timezone=True)`
- 模型字段：`Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))`

### 5.10 Enum
- 所有业务枚举继承 `StrEnum`（Python 3.11+）
- SQLAlchemy 映射必须加 `values_callable=lambda e: [m.value for m in e]`，否则 DB 存的是成员名而不是值
- **不要**用老式 `class Foo(str, Enum)`（会触发 ruff UP042）

### 5.11 SQLAlchemy 惯用法
- 布尔列查询用 `.is_(True)` 而非 `== True`（避免 E712）
- async session 只用 `selectinload()` 载关联，不用 `joinedload()`（与 async 兼容性更好）
- 模型关系必须标明 `back_populates` 或 `viewonly`

### 5.12 测试
- Backend：`pytest` + `pytest-asyncio`（`asyncio_mode = "auto"`），测试在 `backend/tests/` 下
- 单元测试放 `tests/unit/`，集成测试放 `tests/` 根目录
- `conftest.py` 提供 `db_session`（空 DB + savepoint rollback）和 `seeded_db_session`（含 seed 数据）两种 fixture，选用取决于测试需要
- 新增 service 函数**必须**伴随对应单元测试
- Frontend：`vitest` + `@testing-library/react`，配置在 `vitest.config.ts`
- 测试文件放在被测文件旁边（`*.test.ts(x)`）或 `__tests__/` 目录
- UI 组件用 `renderWithProviders`（`src/test/utils.tsx`）包裹 ConfigProvider + Router + i18n
- 跑测试：`cd backend && pytest tests/`、`cd frontend && npm test`
- 覆盖率：`pytest --cov=app` / `npm run test:coverage`

### 5.13 Cerbos 授权
- 字段级读权限由 Cerbos sidecar 评估（`deploy/cerbos-policies/*.yaml`）
- 新增 resource 的字段权限：在 `deploy/cerbos-policies/` 加对应 YAML，遵循现有 4 个文件的格式
- `backend/app/core/cerbos_client.py` 封装 HTTP 调用，**不直接调 Cerbos API**
- Cerbos 不可达时自动降级到 `core/field_authz.py` 的静态 `FIELD_PERMISSIONS` dict（零故障风险）
- 修改权限规则后 Cerbos 自动热加载（`watchForChanges: true`），不需要重启容器
- **不要**在业务代码里直接引用 `FIELD_PERMISSIONS` dict，统一走 `cerbos_client.check_field_access` / `filter_dict_via_cerbos`

### 5.14 SAML SSO
- SAML 配置统一通过 `system_parameters` 的 `auth.saml.*` 键管理，不再依赖写死在环境变量里的 IdP 参数
- 登录入口：`GET /api/v1/auth/login-options` → `GET /api/v1/saml/login` → `POST /api/v1/saml/acs`
- 首次 SAML 登录支持 JIT 自动建用户；若命中已有本地邮箱账号，则自动关联为 `auth_provider="saml"`
- 组映射可选：`auth.saml.group_mapping_enabled=true` 时，按 `auth.saml.group_mapping` JSON 顺序匹配用户组 → 本地角色/部门
- 未开启组映射或无匹配时，自动创建用户必须回退到最低权限默认角色（当前 `requester`）

## 6. 代码质量门禁

### 6.1 CI 检查（`.github/workflows/ci.yml`）

必须全绿才能合并：

```bash
# Backend
cd backend
ruff check app                      # lint
ruff format --check app             # 格式

# Frontend
cd frontend
npm run type-check                  # tsc --noEmit
npm run build                       # 生产构建

# Docker
cd deploy && docker compose build   # 所有镜像构建通过
```

### 6.2 本地一键验证

没有独立的 `scripts/verify.sh`，但常用组合：

```bash
# Backend 完整检查
cd backend && ruff check app && ruff format --check app

# Frontend 完整检查
cd frontend && npm run type-check && npm run build

# E2E 回归
cd deploy && docker compose down && docker volume rm mica_postgres_data
docker compose up -d && sleep 15
# 之后跑项目 e2e 脚本（或手动 curl 关键端点）
```

### 6.3 常见坑

- **`docker compose build --no-cache` 不一定真 bust**。改前端代码后最稳做法：
  ```bash
  docker compose rm -sf frontend && docker image rm mica-frontend:0.4.0
  docker compose build frontend && docker compose up -d frontend
  ```
- **e2e 脚本假设 fresh DB**：累积运行会因 SKU 样本累加而误报。跑 e2e 前先 `docker volume rm mica_postgres_data`。
- **Alembic 版本乱**时最稳做法是 drop volume 重来，不要手动 UPDATE `alembic_version`
- **登录端点区分**：`/api/v1/auth/login` 是 OAuth2 form-urlencoded；`/api/v1/auth/login/json` 是 JSON body

## 7. 文档与决策

| 文档 | 用途 |
|---|---|
| [README.md](./README.md) | 项目门面、版本路线、一页概览 |
| [CHANGELOG.md](./CHANGELOG.md) | 按版本归档变更（Keep-a-Changelog 风格） |
| [docs/QUICKSTART.md](./docs/QUICKSTART.md) | 3 分钟启动 + v0.5 功能速览 |
| [docs/DEVELOPMENT.md](./docs/DEVELOPMENT.md) | 非 Docker 开发、添加 API / 系统参数 / 审批规则 / 通知类型 |
| [docs/adr/0001-technology-stack.md](./docs/adr/0001-technology-stack.md) | 技术栈锁定 + 实施偏差记录 |
| [docs/adr/0002-search-pg-trgm-over-zhparser.md](./docs/adr/0002-search-pg-trgm-over-zhparser.md) | 全文检索选型决策 |
| [docs/adr/0003-system-parameters.md](./docs/adr/0003-system-parameters.md) | 系统参数集中配置决策 |
| [docs/user-manual/](./docs/user-manual/) | 业务用户手册（已部署到 GitHub Pages） |
| [deploy/scripts/README.md](./deploy/scripts/README.md) | 运维脚本用法 + cron 示例 + 故障排查 |

## 8. Git / 协作准则

- **Conventional Commits**：`feat:` / `fix:` / `refactor:` / `chore:` / `docs:` / `test:` / `style:` / `perf:`
- **不随意 push**：除非用户明确要求
- **不 `git rebase -i` / `--no-verify` / `--amend`**（amend 仅在 pre-commit hook 自动改了文件时用）
- **不 `git reset --hard`** 除非用户明确要求
- **不动 `deploy/docker-compose.yml`** 除非必要（影响部署稳定性）
- **提交前跑本地 lint + build**：不要让 CI 替你发现基础错误

### 合理 commit 粒度

- 一个 commit 做**一类事**：只改 backend 接口 / 只加文档 / 只做前端页面
- commit body 解释 **why**，不只是 **what**
- **不要**在 commit message 里写"由某某工具/助手生成"之类的元信息

## 9. 未完待续

详见 [CHANGELOG.md](./CHANGELOG.md) "版本路线（规划中）" 章节。当前 v0.8.0 已交付；v0.9 候选主题：
- 飞书集成（消息通知 + 审批卡片联动）
- 覆盖率硬阈值（backend 70% / frontend 60%）+ E2E 浏览器测试
- 批量导入 Excel
- 真实 LLM 模型接通演示

新功能进入开发前，建议先看 [CHANGELOG.md](./CHANGELOG.md) 和相关 ADR，避免与既有设计冲突。

---

## 10. 一句话指引给 AI assistant

> 看 `README.md` 理解产品，看本文件理解约定，看 `docs/DEVELOPMENT.md` 写新代码，看 `docs/adr/` 理解"为什么是这样"，看 `deploy/scripts/README.md` 解决运维问题。
>
> 严格守 §5 的 11 条约定；修东西前先跑 `ruff check` / `npm run type-check`；不要 push，不要 force-push。
