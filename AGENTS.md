# AGENTS.md — Mica 开发导读

> 本文件供 AI coding assistant（Claude / Copilot / Cursor 等）和人类工程师快速理解 Mica 代码库、约定与常见操作。新 session / 新同事读这一份 + `README.md` + `docs/DEVELOPMENT.md` 即可上手。

---

## 1. 项目一分钟速览

- **Mica（觅采）** — 企业内部采购管理系统（Internal Procurement Management System）
- **规模**：单公司 < 100 员工、月 < 300 单的 IT 部门内部使用
- **License**：Apache 2.0
- **当前版本**：见 `frontend/package.json` / `backend/pyproject.toml` / `backend/app/config.py` / `README.md` 四处版本号同步（参见 §9）· [CHANGELOG.md](./CHANGELOG.md)
- **设计准则**：效率优先 > 扩展性 > 标准化管控（业务上"宁可让 admin 兜底，也不要让流程卡死"）
- **仓库**：`git@github.com:helixzz/mica.git`（main 分支，无 develop / staging 分支）
- **生产环境**：`https://mica.jqdomain.com` · `ssh ubuntu@10.8.252.64` 无密码登录可直接部署

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
│   │   ├── models/__init__.py      # 所有 SQLAlchemy 模型（单文件 ~1700 行，46 个类）
│   │   ├── schemas/__init__.py     # 所有 Pydantic request/response（~1300 行）
│   │   ├── core/                   # security / authz / field_authz / i18n / scoping
│   │   ├── api/
│   │   │   ├── __init__.py         # 聚合 router（v1 + v2 镜像）
│   │   │   └── v1/                 # 30+ REST 端点文件，每文件一个业务域
│   │   │       ├── activity_logs.py   # 资源活动日志（v1.35.0+）
│   │   │       ├── admin.py           # 后台管理（含 audit-logs，整体 admin guard）
│   │   │       ├── purchase.py        # PR/PO + 拆分/履约 link
│   │   │       ├── flow.py            # 合同/付款/发票/到货
│   │   │       ├── dashboard.py       # 仪表盘聚合（无角色 guard，纯前端 UI 取舍）
│   │   │       └── ...
│   │   ├── services/               # 业务逻辑层（每域一文件，purchase.py 最大 ~2300 行）
│   │   └── i18n/messages/          # zh-CN.json / en-US.json
│   ├── migrations/versions/        # Alembic 迁移文件（0001 - 0052+，编号严格连续）
│   └── pyproject.toml              # 依赖 + ruff 配置
├── frontend/
│   └── src/
│       ├── theme/                  # tokens + AntD theme + ThemeProvider
│       ├── styles/global.css       # CSS vars + print + responsive
│       ├── components/
│       │   ├── Layout/AppLayout.tsx     # 应用外壳（可收起侧边栏）
│       │   ├── ui/                      # PageHeader / StatCard / Section / EmptyState
│       │   ├── ActivityTimeline.tsx     # 通用资源活动日志组件
│       │   ├── ItemPickerWithCreate.tsx # SKU 选择器（可现场创建）
│       │   ├── PR/                      # PR 业务组件
│       │   │   ├── ConvertToPOModal.tsx        # 3 Tab 拆分向导
│       │   │   └── AddSupplementaryFromPRModal.tsx  # PR 行配套补充
│       │   └── PO/                      # PO 业务组件
│       │       ├── ItemsTab.tsx                 # POItem CRUD
│       │       └── SupplementaryItemModal.tsx
│       ├── pages/                  # 30+ 页面（每业务视图一个 .tsx 或目录）
│       ├── stores/                 # Zustand stores
│       ├── api/                    # axios 封装 + 业务 API wrappers (single file)
│       ├── routes/index.tsx        # 路由表
│       ├── i18n/locales/           # zh-CN / en-US common.json (~1400 keys each)
│       ├── auth/                   # 登录态
│       └── assets/illustrations/   # 水獭 SVG 插画
├── deploy/
│   ├── docker-compose.yml          # postgres / migrate / backend / frontend / nginx / cerbos / scheduler
│   ├── .env.example
│   ├── nginx/conf.d/mica.conf
│   ├── cerbos-policies/            # YAML 字段级授权策略（运行时热加载）
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

### 5.15 前后端权限对齐（高频踩坑）

- **每次后端改动 `require_roles(...)`，必须同步检查前端是否有对应的 `can*` 布尔判断**
- 反过来也对：增加新前端按钮时，确认后端端点对应角色匹配
- **典型对齐位置**：
  - `frontend/src/pages/PurchaseOrders/PODetail.tsx` 的 `canCreateContract` / `canWriteSchedule` / `canDeletePO`
  - `frontend/src/pages/ContractDetail.tsx` 的 `canWrite` / `canDelete` / `canTransition` / `canEditSchedule`
  - `frontend/src/pages/Contracts.tsx` 同上
  - `frontend/src/pages/RFQDetail.tsx` 的 `canEdit`
  - `frontend/src/components/PO/ItemsTab.tsx` 的 `canEdit`
- **审计命令**（在 mica/frontend/）：
  ```bash
  grep -rnE "\[.*'(admin|procurement_mgr|it_buyer|finance_auditor|dept_manager|requester)'.*\]\.includes\(.*role" src/
  ```
- **历史教训**：v1.33.3 / v1.33.4 一次性补齐了 6 处前端漏配 it_buyer 的按钮——它们都是后端早已允许、但前端 UI 一直不显示，用户报告"找不到按钮"才发现

### 5.16 Async ORM 序列化（避免 MissingGreenlet）

任何**返回 ORM 对象给 Pydantic `model_validate()` 序列化**的服务函数：

- ❌ **错误模式**：`await db.commit()` → `return await db.get(SomeModel, id)`
- ✅ **正确模式**：`await db.commit()` → `select(SomeModel).options(selectinload(needed_relations))` 重新查询

**为什么**：生产环境 `expire_on_commit=True`，commit 后实例属性被 expire。Pydantic 访问关系字段（如 `POItem.fulfillment_links`）时触发懒加载，但 SQLAlchemy 异步 greenlet 上下文已结束 → `MissingGreenlet` → 500

**测试遮蔽**：`conftest.py` 用 `expire_on_commit=False`，单测可能不重现。所以**`test_xxx_returns_obj` 必须显式调 `OutputSchema.model_validate(obj)` 来跑序列化路径**

历史教训：v1.30.0 → v1.30.1 hotfix 即此问题；v1.31.0 / v1.33.0 后所有相关函数都遵守此规则。审计命令：
```bash
grep -rn "await db.get" backend/app/services/purchase.py
```

### 5.17 React Hooks 顺序（避免 React #310）

每个 React 函数组件的所有 `useState/useEffect/useMemo/useCallback/useAuth/useToken` **必须在任何 early return 之前**：

```jsx
// ❌ 错误：early return 后再有 hook
function PRDetail() {
  const [pr, setPr] = useState(null)
  if (!pr) return <Loading />       // EARLY RETURN
  const items = useMemo(...)         // 渲染次数不一致 → React #310
}

// ✅ 正确
function PRDetail() {
  const [pr, setPr] = useState(null)
  const items = useMemo(() => pr ? ... : [], [pr])  // memo 自己处理 null
  if (!pr) return <Loading />
}
```

历史教训：v1.28.0 → v1.28.2 即此问题，用户看到的是"500"错误页（ErrorBoundary 捕获后渲染）但实际是 React minified error。

审计技巧：每次新加 hook，scroll up 确认前面没有 `if (!x) return` 类型的语句。

### 5.18 i18n 双语 parity 检查

每次加 i18n key 必须 zh + en 同步加。验证脚本：

```bash
# Backend
cd backend && .venv/bin/python -c "
import json
zh=json.load(open('app/i18n/messages/zh-CN.json'))
en=json.load(open('app/i18n/messages/en-US.json'))
def w(d,p=''): return {f'{p}.{k}' if p else k for k,v in d.items() for k_ in (w(v,f'{p}.{k}' if p else k) if isinstance(v,dict) else {None})} if False else (lambda f:f(f))(lambda f: {f'{p}.{k}' if p else k for k,v in d.items() if not isinstance(v,dict)} | set().union(*(f.__wrapped__ if hasattr(f,'__wrapped__') else set() for v in d.values() if isinstance(v,dict))))
# 实际简版：
def walk(d, p=''):
    out = set()
    for k, v in d.items():
        kk = f'{p}.{k}' if p else k
        if isinstance(v, dict): out |= walk(v, kk)
        else: out.add(kk)
    return out
print('zh-en diff:', walk(zh) - walk(en))
print('en-zh diff:', walk(en) - walk(zh))
"

# Frontend
cd frontend && node -e "
const zh = require('./src/i18n/locales/zh-CN/common.json');
const en = require('./src/i18n/locales/en-US/common.json');
const walk = (d,p='') => Object.keys(d).flatMap(k => typeof d[k] === 'object' ? walk(d[k], p+k+'.') : [p+k]);
console.log('zh-only:', walk(zh).filter(k => !new Set(walk(en)).has(k)).filter(k=>!k.startsWith('insights.')));
console.log('en-only:', walk(en).filter(k => !new Set(walk(zh)).has(k)));
"
```

前端有 7 个历史 `insights.*` 键 zh-only（pre-existing），可忽略。

### 5.19 履约模型语义（PR ↔ PO 多对多）

PR 需求和 PO 履约通过 `pr_fulfillment_links` 表多对多关联，每条 link 标记一个**履约类型**：

| 类型 | 语义 | 计入进度条 | 受 1.5x 软上限约束 |
|---|---|---|---|
| `equivalent` | 完全等价 | ✅ | ✅ |
| `downgraded` | 降配（仍计入 PR 行数量） | ✅ | ✅ |
| `substitute` | 替换型号（不同物料、相同需求） | ✅ | ✅ |
| `supplementary` | 配套补充（不同 uom，例如 1024 GPU 配 64 服务器） | ❌ | ❌ |

**关键不变量**：
- 进度条 `fulfilled_qty` 只算前 3 种（uom 一致）；supplementary 在 `fulfillment_breakdown` 字典里单独展示
- PR 状态机基于前 3 种判断 `partially_converted` / `converted`
- 修改 `_compute_pr_status_after_link_change` 时**绝不能把 supplementary 加进 fulfilling_types**（v1.33.1 → v1.33.2 即此回滚）
- supplementary 可指向任意供应商，允许独立 PO（一个 PR 行的服务器主体走供应商 X，配件可独立 PO 走供应商 Y）

### 5.20 Activity Log 范围与权限

- **业务活动日志**（用于资源详情页 Activity Timeline）：`GET /v1/resource-activity-logs?resource_type=X&resource_id=Y` — 无角色 guard，访问控制通过资源本身的 visibility（`get_pr` / `get_po` 等）
- **管理审计日志**（用于 Admin 后台）：`GET /v1/admin/audit-logs` — admin guard
- 业务日志端点黑名单事件前缀：`auth.*`, `admin.*`, `notification.*`（保留给 admin 端点）
- 业务日志端点白名单 resource_type：PR/PO/POItem/Contract/RFQ/Invoice/PaymentRecord/Shipment/PRFulfillmentLink

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

## 9. 版本发布流程（强制规定，不可跳过）

**每次代码修改（包括 bugfix 和 new feature）必须执行完整发布流程：**

1. **Bump version** — 同时修改以下 4 个文件中的版本号：
   - `frontend/package.json` → 第 4 行 `"version": "X.Y.Z"`
   - `backend/pyproject.toml` → 第 3 行 `version = "X.Y.Z"`
   - `backend/app/config.py` → `app_version: str = "X.Y.Z"`
   - `README.md` → 第 13 行 `version-X.Y.Z` badge URL

2. **Create Release** — `gh release create vX.Y.Z --title "vX.Y.Z — 简短描述" --notes "详细 changelog"`

3. **Deploy** — `ssh` + `docker compose up -d --build` 到生产环境

4. **Update CHANGELOG.md** — 补充该版本的入口

**不 bump version → 不部署 → 不视为完成。**

**所有新增功能和 bug 修复必须完成端到端测试（E2E）后才视为正式交付。** 修改后端代码后应 `curl` 生产环境关键端点验证返回；修改前端代码后应在浏览器中确认交互流程正常。不可仅凭 `ruff check` 或 `tsc --noEmit` 通过就声称已完成。

---

## 10. 一句话指引给 AI assistant

> 看 `README.md` 理解产品，看本文件理解约定，看 `docs/DEVELOPMENT.md` 写新代码，看 `docs/adr/` 理解"为什么是这样"，看 `deploy/scripts/README.md` 解决运维问题。
>
> 严格守 §5 的 11 条约定；修东西前先跑 `ruff check` / `npm run type-check`；不要 push，不要 force-push。
