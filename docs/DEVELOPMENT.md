# 开发者指南

## 本地开发（非 Docker 方式）

### 后端

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# 启动 Postgres（用 Docker 最方便）
docker run -d --name mica-pg -p 5432:5432 \
  -e POSTGRES_USER=mica -e POSTGRES_PASSWORD=mica -e POSTGRES_DB=mica \
  postgres:16-alpine

# 运行迁移
alembic upgrade head

# 启动 API
uvicorn app.main:app --reload
```

- API 文档：<http://localhost:8000/api/docs>
- 首次启动会自动种子化 demo 数据（由 `app.services.seed.seed_dev_data` 驱动）

### 前端

```bash
cd frontend
npm install
npm run dev
```

- 前端开发服务器：<http://localhost:5173>
- 请求通过 Vite proxy 转到 <http://localhost:8000/api>
- 默认代理目标可通过 `VITE_API_TARGET` 覆盖

## 项目目录约定

```
backend/
├── app/
│   ├── main.py            # FastAPI 入口
│   ├── config.py          # pydantic-settings
│   ├── db/                # SQLAlchemy engine + session
│   ├── models/            # ORM
│   ├── schemas/           # Pydantic request/response
│   ├── core/              # security, deps
│   ├── i18n/              # 后端消息字典 + messages/*.json
│   ├── api/v1/            # FastAPI routers
│   └── services/          # 业务逻辑
├── migrations/            # Alembic
└── tests/
frontend/
├── src/
│   ├── api/               # axios + DTO + API 函数
│   ├── auth/              # 登录态
│   ├── i18n/              # react-i18next + locales/
│   ├── components/        # Layout, LanguageSwitcher, GlobalSearch, NotificationBell, ui/*
│   ├── pages/             # 每个业务视图一个目录
│   ├── stores/            # Zustand（notification 等）
│   ├── theme/             # tokens.ts / antdTheme.ts / ThemeProvider.tsx
│   ├── styles/            # global.css（CSS vars + print + 响应式）
│   ├── assets/            # illustrations/otter-*.svg 等
│   └── routes/
deploy/
├── docker-compose.yml
├── .env.example
├── nginx/conf.d/mica.conf
└── scripts/               # dev-up / dev-down / backup / restore / upgrade / health / logs
```

## 数据库迁移

```bash
cd backend
# 生成新迁移
alembic revision --autogenerate -m "add foo table"

# 应用
alembic upgrade head

# 回滚一步
alembic downgrade -1
```

生产部署：`migrate` 容器在每次 `docker compose up` 时自动运行 `alembic upgrade head`，backend 等待其完成后才启动。

## 添加新语言 / 新翻译 Key

### 后端
- 编辑 `backend/app/i18n/messages/zh-CN.json` 和 `en-US.json`
- 代码中：`from app.i18n import t; raise HTTPException(400, detail=t("pr.no_items", locale))`

### 前端
- 编辑 `frontend/src/i18n/locales/{zh-CN,en-US}/common.json`
- 组件中：`const { t } = useTranslation(); t("button.submit")`
- 新模块建议新建 namespace，例如 `purchase.json`，在 `frontend/src/i18n/index.ts` 注册

## 代码质量

```bash
# 后端
cd backend
ruff check app
ruff format app
mypy app

# 前端
cd frontend
npm run type-check
```

## 测试

### 后端
```bash
cd backend
# 需要 Postgres test DB
createdb mica_test   # 或 docker exec mica-postgres createdb -U mica mica_test
pytest -m integration
```

## 添加 API 路由

1. 在 `backend/app/api/v1/` 新建 `my_module.py`
2. 在 `backend/app/api/__init__.py` `api_router.include_router(...)`
3. 业务逻辑放 `backend/app/services/`
4. 数据模型放 `backend/app/models/`（现在单一 `__init__.py`，未来按领域拆分）
5. 前端 `src/api/index.ts` 增加对应调用

## 添加系统参数（v0.5+）

当需要新增一个 **可配置阈值** 时，不要直接硬编码常量：

1. 在 `backend/migrations/versions/` 新增迁移，通过 `op.bulk_insert` 加一行到 `system_parameters`：
   ```python
   {
     "key": "myfeature.max_items",
     "category": "myfeature",
     "value": 100,
     "default_value": 100,
     "data_type": "int",
     "min_value": 1,
     "max_value": 1000,
     "unit": "count",
     "description_zh": "X 功能的最大条数",
     "description_en": "Maximum items for X feature",
   }
   ```
2. 在对应服务里读取：`from app.services.system_params import system_params; limit = await system_params.get_int(db, "myfeature.max_items")`
3. 前端 Admin 控制台的 "系统参数" Tab **自动显示**（无需改代码），按 category 折叠

参见 [ADR 0003](./adr/0003-system-parameters.md)。

## 配置 SAML SSO（v0.8.1+）

Mica 的 SAML/ADFS 集成通过 `system_parameters` 中的 `auth.saml.*` 键进行管理员可视化配置。

### 关键参数

- `auth.saml.enabled`
- `auth.saml.idp.entity_id`
- `auth.saml.idp.sso_url`
- `auth.saml.idp.slo_url`
- `auth.saml.idp.x509_cert`
- `auth.saml.sp.entity_id`
- `auth.saml.sp.acs_url`
- `auth.saml.attr.email`
- `auth.saml.attr.display_name`
- `auth.saml.attr.groups`
- `auth.saml.jit.enabled`
- `auth.saml.jit.default_role`
- `auth.saml.jit.default_company_code`
- `auth.saml.jit.default_department_code`
- `auth.saml.group_mapping_enabled`
- `auth.saml.group_mapping`

### 运行机制

1. 管理员在 **Admin → System Parameters** 中维护 `auth.saml.*` 参数。
2. 登录页调用 `/api/v1/auth/login-options`，若 `saml_enabled=true` 则显示 “通过 SSO 登录”。
3. 用户点击后进入 `/api/v1/saml/login`，由后端发起 SAML AuthnRequest。
4. IdP 回调 `/api/v1/saml/acs` 后：
   - 校验签名与响应
   - 按属性名提取邮箱 / 显示名 / 用户组
   - JIT 自动建用户或关联已有本地邮箱账号
   - 生成 JWT 并跳转到 `/sso-callback#token=...`
5. 前端 `SsoCallbackPage` 保存 token、加载当前用户并跳回业务页。

### 组映射格式

```json
[
  {"group": "Finance", "role": "finance_auditor", "department_code": "FIN"},
  {"group": "IT Managers", "role": "dept_manager", "department_code": "IT"}
]
```

- first match wins
- 未开启组映射或未命中时，自动创建用户回退到 `auth.saml.jit.default_role`

## 添加审批规则（v0.5+）

多级串签通过 `approval_rules` 表配置：

```python
{
  "name": "付款审批（大额）",
  "biz_type": "payment",
  "amount_min": 500000,
  "amount_max": None,
  "department_ids": None,        # v1.37.0+: NULL = 适用所有部门；非空数组 = 仅这些部门
  "cost_center_ids": None,       # v1.37.0+: 同上
  "stages": [
    {"stage_name": "财务审核", "approver_role": "finance_auditor", "order": 1},
    {"stage_name": "CFO 审批", "approver_role": "procurement_mgr", "order": 2},
  ],
  "is_active": True,
  "priority": 10,
}
```

创建方式：通过 Admin 控制台 / `POST /api/v1/approval-rules` 或 Alembic seed 迁移。`services/approval.py:_match_rule` 在处理 PR 提交时按以下条件依次过滤：

1. `biz_type` 严格相等
2. `is_active = true`
3. `amount_min ≤ amount < amount_max`（任一可为 NULL = 无下/上限）
4. PR 的 `department_id ∈ department_ids` 或 `department_ids` 为 NULL
5. PR 的 `cost_center_id ∈ cost_center_ids` 或 `cost_center_ids` 为 NULL

最终按 `priority asc, created_at asc` 取第一条。

### 多维度规则示例（v1.37.0+）

```python
# 例 1：IT 部门的所有 PR 走简化审批（一阶 admin）
{
  "name": "IT 简化",
  "biz_type": "purchase_requisition",
  "amount_min": None, "amount_max": 50000,
  "department_ids": ["<IT-dept-uuid>"],
  "cost_center_ids": None,
  "stages": [{"stage_name": "管理员审批", "approver_role": "admin", "order": 1}],
  "priority": 1,
}

# 例 2：科研项目成本中心的所有 PR 必须经科研主管 + 财务双签
{
  "name": "科研项目双签",
  "biz_type": "purchase_requisition",
  "department_ids": None,
  "cost_center_ids": ["<research-cc-uuid>"],
  "stages": [
    {"stage_name": "科研主管", "approver_role": "dept_manager", "order": 1},
    {"stage_name": "财务复核", "approver_role": "finance_auditor", "order": 2},
  ],
  "priority": 5,
}
```

**Tip**：留 `department_ids = NULL` 的「兜底规则」放在低优先级（`priority` 大），保证特殊规则优先命中。

### 路由解析（v1.36.0+）

审批人解析按以下优先级（`_resolve_routing_context`）：

1. **指定 `department_id`**：直接按该部门解析（IT 代提业务部门时使用）
2. **指定 `requester_id`** 且非 actor：按 requester 的 `department_id`/`company_id` 解析
3. **回退**：按 actor 的 `department_id`/`company_id` 解析

`_resolve_user_for_role` 在解析 `dept_manager` 时启用部门树形回溯（`approval.dept_manager_chain_lookup` 默认 true）：当当前部门没有该角色用户，沿 `Department.parent_id` 往上找直到根，仍找不到才落 admin 兜底。

### 申请人指定审批人（v1.36.0+）

`PRCreateIn.preferred_first_approver_id` 允许申请人指定第一阶审批人：

- 提交时调用 `validate_preferred_approver_or_raise`：若指定人不在规则解析的第一阶候选集 → 422 + candidates 列表
- 命中候选集 → 第一阶仅创建一条 task 给该人，其他候选人不入
- 任务 meta 写入 `preferred_by_submitter: true` 便于审计
- 系统参数 `approval.allow_submitter_preferred_approver` 默认 true，admin 可全局关闭

### 审批链预览（v1.36.0+）

`POST /api/v1/approval/preview` 接收 `{biz_type, amount, requester_id?, department_id?, cost_center_id?}` 返回完整审批链 + 每阶段候选人。前端 PRNew 实时调用展示给用户。该端点仅要登录、不限角色（与 dashboard 端点一致）。

## 添加通知类型（v0.5+）

新增一种通知场景：

1. 在 `NotificationCategory` enum 添加新值（`backend/app/models/__init__.py`）
2. 在业务服务的合适位置调用 `create_notification(db, user_id=..., category=NotificationCategory.X, title=..., link_url=..., biz_type=..., biz_id=..., meta={...})`
3. 在 i18n 添加 `notification.x.xxx` 翻译 key（zh-CN + en-US）
4. 前端 `components/NotificationBell/NotificationBell.tsx` 的 category → 图标/颜色 map 加一条

## 运维脚本（v0.5+）

`deploy/scripts/` 下有 5 个 pure bash 脚本：

- `health.sh` — 健康检查（人读 + `--json`）
- `backup.sh` — 备份 DB + media volume
- `restore.sh` — 从备份恢复
- `upgrade.sh` — 一键升级（自动备份 + 失败回滚）
- `logs.sh` — 容器日志聚合

脚本设计原则：纯 bash + `docker compose` + `curl`，无 Python/Node 依赖。详见 `deploy/scripts/README.md`。

## 里程碑

见 [CHANGELOG.md](../CHANGELOG.md) 与 [README.md](../README.md) 的"版本路线"章节。

## 测试（v0.6+）

### Backend（pytest）

```bash
cd backend
source .venv/bin/activate
pytest tests/                         # 全量
pytest tests/unit/test_approval.py -v # 单文件
pytest --cov=app --cov-report=term    # 覆盖率
```

- `tests/conftest.py`：SAVEPOINT rollback pattern 保证每 test 隔离
- `db_session`：空 DB（schema + migration seed）
- `seeded_db_session`：含 `seed_dev_data` 的 5 个用户 + 主数据
- `client`：httpx AsyncClient 走 FastAPI dependency_overrides

测试数据库用 `mica_test`（第一次需手动创建：`docker exec mica-postgres psql -U mica -d postgres -c "CREATE DATABASE mica_test OWNER mica"`）。

### Frontend（vitest）

```bash
cd frontend
npm test          # 全量
npm run test:watch # 监听
npm run test:coverage # 覆盖率
```

- `vitest.config.ts`：jsdom + @vitest/coverage-v8
- `src/test/setup.ts`：matchMedia / ResizeObserver / IntersectionObserver polyfills（AntD 5 依赖）
- `src/test/utils.tsx`：`renderWithProviders`（ConfigProvider + MemoryRouter + I18nextProvider）

### CI

`.github/workflows/ci.yml` 有 5 个 job：backend lint / backend test + coverage / frontend lint + build / frontend test + coverage / docker build。
覆盖率上传到 Codecov（双 flag：backend / frontend）。

## 分类管理（v0.6.2+）

### 添加新的分类维度

如果是**纯枚举**（2-5 个值，不需要独有字段）：

1. 在 `lookup_values` 表加 rows（`type='your_new_dimension'`），可通过 migration 或 Admin UI
2. 前端调 `api.listLookupValues('your_new_dimension')` 获取下拉选项

如果**有独有字段**（预算、层级、关联关系）：

1. 新建独立表 + migration
2. 新建 model + relationship
3. 新建 API endpoint

### 添加采购种类（L2 子分类）

1. Admin → 分类管理 → 采购种类 → "添加" → 选择上级分类
2. 或 API：`POST /admin/procurement-categories { code, label_zh, label_en, parent_id }`

## Cerbos 授权（v0.6+）

### 架构

```
backend ──(HTTP)──> cerbos sidecar (:3593)
                    ├── purchase_requisition.yaml
                    ├── purchase_order.yaml
                    ├── payment_record.yaml
                    └── invoice.yaml
```

### 添加新 resource 的字段权限

1. 在 `deploy/cerbos-policies/` 加一个 YAML 文件，格式参照现有 4 个
2. 在 `core/field_authz.py` 的 `FIELD_PERMISSIONS` dict 加对应项（作为 fallback）
3. Cerbos 自动热加载（`watchForChanges: true`），不需要重启容器

### Graceful fallback

Cerbos 不可达时（如开发环境没启动 cerbos 容器），`cerbos_client.py` 自动降级到 `FIELD_PERMISSIONS` 静态 dict。零故障风险。

## PR → PO 履约偏离模型（v1.26+）

业务现实：PR 申请的 64 台完整服务器，履约时可能因供货问题变成 32 台完整 + 16 台缺 A 配件 + 16 台缺 A/B 配件 + 32 套 A 配件 + 16 套 B 配件，每部分可能来自不同供应商。

### 数据模型

`pr_fulfillment_links` 表把 POItem 与 PRItem 多对多关联（迁移 0050 + 0051）：

```
pr_fulfillment_links
├── pr_item_id        FK → pr_items.id (CASCADE)
├── po_item_id        FK → po_items.id (CASCADE)
├── qty_contribution  Numeric        — 该 POItem 顶替 PR 行的数量
├── fulfillment_type  enum           — equivalent / downgraded / substitute / supplementary
├── deviation_note    text           — 采购员填写偏离原因
└── created_by_id     FK → users.id

UNIQUE (pr_item_id, po_item_id)  -- 同一对组合只能有一条 link
```

### 4 种履约类型语义

| 类型 | 业务含义 | 计入 fulfilled_qty 进度 | 受 1.5x 软上限约束 |
|---|---|---|---|
| `equivalent` | 完全等价 | ✅ | ✅ |
| `downgraded` | 同型号缺配件，仍记入主履约数量 | ✅ | ✅ |
| `substitute` | 替换型号，仍记入主履约数量 | ✅ | ✅ |
| `supplementary` | 配套补充（不同 uom，例如 GPU 配服务器） | ❌ 仅 breakdown 单独显示 | ❌ |

### 关键服务函数

- `convert_pr_to_po(db, actor, pr_id)` — 一键全转，按 PR 行 supplier 分组创建 PO
- `convert_pr_to_po_partial(db, actor, pr_id, pr_item_ids)` — 选行整转
- `convert_pr_to_po_with_specs(db, actor, pr_id, specs)` — 自定义拆分；每个 spec 可指定 qty / unit_price / supplier / item_id / type / deviation_note
- `add_supplementary_for_pr_item(db, actor, pr_item_id, ...)` — 事后给某个 PR 行加配套补充项，可开新 PO 也可追加到现有 PO
- `update_po_item / delete_po_item` — POItem CRUD，自动同步 PO total + link.qty_contribution + PR 状态

### PR 状态机

`_compute_pr_status_after_link_change(db, pr)`：

1. 查询所有 `fulfillment_type IN (equivalent, downgraded, substitute)` 的 link 按 pr_item 聚合 qty
2. 对每个 PR 行：若 `summed_qty >= pr_item.qty` 则视为完全履约
3. 全部完全履约 → `converted`；部分 → `partially_converted`；零 → `approved`（即使之前是 converted）

**`SUPPLEMENTARY` 不参与状态计算**（v1.33.1 → v1.33.2 教训：不同 uom 会让数字爆掉，例如 1024 GPU + 64 服务器 = 1088/64 看起来溢出）。

## 资源活动日志（v1.35.0+）

业务用户的活动时间线端点：`GET /v1/resource-activity-logs?resource_type=X&resource_id=Y`

- 无角色 guard
- 通过资源 visibility（`get_pr` / `get_po` / 等）做访问控制
- 黑名单事件：`auth.*` / `admin.*` / `notification.*` 不返回
- 白名单 resource_type：PR / PO / POItem / Contract / RFQ / Invoice / PaymentRecord / Shipment / PRFulfillmentLink

后台审计日志 `GET /v1/admin/audit-logs` 保留 admin 专用（在 admin router 整体 guard 下）。

## Dashboard 端点（v1.34+）

`/v1/dashboard/*` 全部端点**仅要登录、不限角色**。任何 `(isProcurementMgr || isFinanceAuditor || role === 'admin')` 类型的前端 gate 都是 UI 取舍，不是权限边界。it_buyer / requester / dept_manager 都可以调用所有 dashboard 接口。
