# Changelog

All notable changes to Mica will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [v0.8.8] — 2026-04-23

### 修复

- **AI 路由面板删除模型后不刷新**：删除 LLM 模型后切换到"AI 场景路由"Tab，被删模型仍显示在路由下拉选择中。根因：Admin Tabs 不卸载非活跃面板，路由面板的模型列表只在首次挂载时加载。修复：加 `destroyInactiveTabPane`，切换 Tab 时重新加载数据
- **成本中心操作语义清晰化**：恢复删除按钮（后端实为软删除），与编辑/启停分开；删除 toast 改为"已删除"而非之前误导性的"已停用"

## [v0.8.7] — 2026-04-23

### 修复

- **禁用公司主体后从列表消失**：`GET /companies` 端点硬编码 `is_active=True` 过滤。新增 `include_inactive` 查询参数，Admin 页传 `true` 显示全部（业务表单下拉仍只显示活跃公司）
- **成本中心"删除"实为停用但行为不一致**：后端 `delete_cost_center` 实际是软删除（`is_active=False`），但 UI 用垃圾桶图标且停用后条目消失。修复：成本中心改为编辑/启用/停用操作（去掉误导性垃圾桶图标），Admin 列表请求包含已停用条目，状态列可见

## [v0.8.6] — 2026-04-23

### 修复

- **公司主体停用不生效**：`CompanyUpdate` schema 和 `update_company()` 服务均缺少 `is_active` 字段处理，导致 PATCH 请求静默丢弃该字段
- **成本中心只能添加/删除**：新增编辑按钮（修改名称/排序）和启用/停用切换按钮，复用已有 `PUT /admin/cost-centers/{id}` 端点；`CostCenterIn` schema 新增 `is_active` 字段

## [v0.8.5] — 2026-04-23

### 修复

- **公司主体无法编辑/停用**：Admin 公司主体 Tab 仅支持新建。新增编辑（修改名称/币种）和启用/停用操作，复用已有 `PATCH /companies/{id}` 后端端点。

## [v0.8.4] — 2026-04-23

### 修复

- **LLM 模型删除 500 错误**：删除被 AI 场景路由引用的模型时触发外键约束冲突（`ai_feature_routing.primary_model_id` FK）。修复后删除前自动将引用该模型的路由 `primary_model_id` 置空，并从 `fallback_model_ids` 数组中移除。

## [v0.8.3] — 2026-04-23

SAML SSO + 审批规则编辑器 + 合同版本管理 + 表单引导 + i18n 插值 Bug 修复。

### 新增

- **SAML SSO 完整能力**：admin 可配置 `auth.saml.*` 系统参数，支持 IdP metadata/login/ACS、JIT 自动建用户、可选用户组→角色映射；登录页 SSO 按钮 + `/sso-callback` token 回调
- **审批规则结构化编辑器**：Form.List 阶段编辑器替代原始 JSON，支持创建/编辑/删除规则，表格内阶段预览
- **合同版本管理基础**：`contract_versions` 表 + 创建时自动快照 + `GET /contracts/{id}/versions` + 详情页"版本历史"Tab
- **表单填写引导**：PR / RFQ / PO / 合同 / SKU / 物料 / Admin 所有高频表单新增 help 文案

### 修复

- **i18n 插值变量未生效**：26 个翻译 key 使用 `{var}` 单大括号而非 react-i18next 要求的 `{{var}}` 双大括号，导致物料总数、合同期次、SKU 异常数等动态文本显示为原始变量名

### 改进

- **运维**：docker-compose.yml 改用 `/data` bind mount（支持独立数据盘）；所有容器 `restart: unless-stopped`

### 测试

- 15 个 SAML backend 测试 + 5 个 frontend SSO 测试 + 3 个审批规则 helper 测试 + 2 个合同版本测试

## [v0.8.2] — 2026-04-23

审批规则结构化编辑 + 合同版本管理基础 + 表单引导第二波。

### 新增

- **审批规则结构化编辑器**：Admin 审批规则从原始 JSON 文本框升级为结构化阶段编辑器（Form.List），支持新建/编辑/删除规则，阶段预览显示在列表。
- **合同版本管理基础能力**：新增 `contract_versions` 表，合同创建时自动保存首版快照，新增 `GET /contracts/{id}/versions` API，合同详情页新增"版本历史"Tab。
- **审批规则 API 扩展**：前端新增 `adminUpdateApprovalRule` 和 `adminDeleteApprovalRule` API 封装。

### 改进

- **表单填写引导（第二波）**：PO 交货/付款/发票、合同付款计划、SKU 报价录入、物料管理、Admin LLM 模型/审批规则/公司主体等高频表单新增 `help` 文案和内联引导。
- **审批规则 UX**：阶段编辑器支持结构化角色选择、排序和预览；移除 React key-spread 警告。

### 测试

- 新增审批规则结构化表单 helper 纯函数测试（3 tests：default/hydrate/serialize）
- 新增合同版本历史服务测试（1 test：降序历史查询）
- 修改合同创建测试验证首版快照自动写入

## [v0.8.1] — 2026-04-23

SAML SSO 基础能力 + 管理端配置 + 首批表单填写引导。

### 新增

- **SAML SSO 后端基础能力**：引入 `python3-saml`，实现 `/api/v1/saml/metadata`、`/api/v1/saml/login`、`/api/v1/saml/acs`，支持 metadata 生成、登录跳转、ACS 回调、JWT 签发。
- **管理员可配置 SAML 参数**：通过 `system_parameters` 新增 `auth.saml.*` 命名空间，覆盖 IdP Entity ID / SSO URL / 证书 / SP Entity ID / ACS URL / 属性映射 / JIT 默认角色 / 默认公司部门 / 组映射开关与 JSON 规则。
- **SAML 登录自动建用户（JIT）**：首次 SAML 登录时自动创建本地用户；若命中已有本地邮箱账号，则自动关联到 `auth_provider="saml"`。
- **可选用户组 → 角色映射**：支持按管理员配置的 JSON 顺序规则，将 SAML 组映射为本地角色与可选部门；未开启或未命中时降级到默认最低权限角色。
- **前端 SSO 登录体验**：登录页新增基于 `/auth/login-options` 的“通过 SSO 登录”入口，新增 `/sso-callback` 页面接收 token、完成登录态加载并跳转回业务页。

### 改进

- **管理员配置引导**：`SystemParamsTab` 为 `auth.saml.*` 参数增加更合适的编辑控件（证书/映射 JSON 多行文本、默认角色下拉）和内联说明。
- **需求方填写引导（第一波）**：为 PR 新建/编辑与 RFQ 新建表单新增用户友好 `help` 文案，明确标题、成本中心、开支类型、采购分类、业务原因、询价截止日期、供应商选择等字段应如何填写。
- **本地 / 测试环境 SAML 兼容性**：对单标签 host（如 `testserver`）启用 `allowSingleLabelDomains`，保证本地测试与开发环境中的 SAML URL 验证通过。

### 修复

- **`requester` 角色约束漂移**：修复 ORM 模型层 `User.role` CHECK 约束仍遗漏 `requester` 的问题，与 0011 migration 保持一致。

### 测试

- 新增 **15 个 SAML 相关 backend tests**：覆盖配置加载、JIT 自动建用户、已有本地账号关联、组映射优先级、禁用 JIT、登录入口可用性、misconfigured 路径、本地密码登录回归。
- 新增 **5 个 frontend tests**：覆盖登录页 SSO 按钮显示/隐藏、点击跳转、`/sso-callback` token 处理与错误路径。

## [v0.8.0] — 2026-04-23

覆盖率硬阈值 + PO 回填 SKU + E2E CI + Bug 修复。

### 新增

- **覆盖率硬阈值**：CI 强制 backend ≥70%、frontend statements/lines ≥60%，低于阈值直接失败
- **PO 成交价自动回填 SKU 价格库**：PR 转 PO 时，为每个有 item_id 的明细行自动创建 `SKUPriceRecord`（source_type=actual_po），使 SKU 行情库自动积累真实采购成交数据
- **E2E 冒烟测试 CI**：Docker Compose 全栈启动 → 健康检查 → 登录 → 6 个核心 API 端点验证，作为 CI 流水线最终门禁

### 修复

- **PR 分类字段未保存**：`create_pr` 和 `update_pr` 遗漏 `company_id`、`cost_center_id`、`expense_type_id`、`procurement_category_id` 四个字段（与 v0.7.3 的 Item category_id bug 同一模式）

### 测试

- 249 backend tests（75% coverage）+ 44 frontend tests（89% statements）
- 新增 export_excel（100%）、export_pdf（100%）、documents（73%）、system_params（82%）测试

---

## [v0.7.3] — 2026-04-22

i18n 全量覆盖 + 权限优化 + Bug 修复。

### 修复

- **物料分类无法保存**：`update_item()` 遗漏 `category_id` 和 `is_active` 字段处理，编辑物料时分类始终显示"未分类"；同步修复 `create_item()` 也补上 `category_id` 赋值
- **RFQ 页面标题显示 raw key**：替换脚本误产生 tab 字符代替 `t` 函数名

### 改进

- **i18n 全量替换**：424 处硬编码中文 → 0，新增 219 个翻译 key（zh-CN + en-US 同步），覆盖全部 21 个组件文件
- **权限放宽**：
  - 供应商增改删：`it_buyer` 可操作（此前仅 admin + procurement_mgr）
  - 分类体系（成本中心 / 开支类型 / 采购种类）9 个写端点：`procurement_mgr` 可操作（此前仅 admin）
  - 付款计划执行：`procurement_mgr` 可操作（此前仅 admin + finance_auditor）

---

## [v0.6.2] — 2026-04-22

采购分类体系 + SKU 行情库可视化增强。

### 新增

- **分类体系（混合架构）**
  - `cost_centers` 独立表：成本中心管理（预留 `budget_amount` / `manager_id`），seed 4 个（IT / 行政 / 产品 / 财务）
  - `procurement_categories` 独立表：2 级层级（`parent_id` 自引用），seed 6 L1 + 4 L2（服务器配件下的内存/SSD/CPU/网卡）；同时服务 PR 分类和 SKU/Item 分类
  - `lookup_values` 通用枚举表：seed expense_type（CapEx / OpEx）；未来新增枚举维度零代码
  - Migration 0008：3 张新表 + PR 加 3 个 nullable FK + Item 加 `category_id` FK
  - 12 个 API 端点：Admin CRUD ×3 + 公开 read + category tree
- **Admin 分类管理 Tab**：成本中心表格 + 采购种类树形展示（L1/L2 标签）+ 开支类型表格 + 统一添加 Modal（含上级分类选择器）
- **PR 创建表单**：新增 3 个可选下拉框（成本中心 / 开支类型 / 采购种类）
- **SKU 分类筛选**：按 procurement_category 过滤物料列表后再多选对比

---

## [v0.6.1] — 2026-04-22

合同付款计划 + SKU 多选价格走势对比图。

### 新增

- **合同付款计划**
  - `payment_schedules` 新表（Migration 0007）：按期管理合同付款，支持 4 种触发类型（fixed_date / milestone / invoice_received / acceptance）
  - 7 个 API 端点：CRUD + execute（创建 PaymentRecord）+ link-invoice + payment-forecast（按月现金流预测）
  - `system_parameters` 新增 `payment.invoice_due_days`（默认 30 天）
  - ContractDetail 页新 Tab"付款计划"：汇总栏（合同/计划/已付/待付）+ 明细表格 + 执行/删除操作 + 新建 Drawer（动态 Form.List）
- **SKU 多选价格走势对比**
  - 多选 Select（搜索 + 清除 + max 6 tags）替代原单选
  - 纯 SVG 交互式折线图：每 SKU 独立颜色线 + 数据点 tooltip + 自动缩放 Y 轴 + 日期标签智能稀疏 + 10 色品牌调色板
  - 每 SKU 基准卡片（均价/最低/最高）
  - `@ant-design/charts` 安装备用

### 测试

- 11 个付款计划单元测试（CRUD / execute / forecast / 边界条件）
- 82 → 82 backend tests pass（+11 新 -0 回归）

---

## [v0.6.0] — 2026-04-22

测试基础设施 + 质量工程 + UI/UX 打磨 + Cerbos 授权外化。首次引入自动化测试（103 个），bundle 代码分割首屏瘦身 97%，LLM 真实接入，审批授权迁移到 Cerbos 策略引擎。

### 新增

- **单元测试基础设施**
  - Backend (pytest)：完全重写 `conftest.py`——SAVEPOINT rollback 隔离、`alembic upgrade head` 替代 `create_all`（保留 migration seed data）、`seeded_db_session` fixture、pytest-asyncio ≥ 0.26 session-scoped loop
  - Frontend (vitest)：`vitest.config.ts` + `setup.ts`（matchMedia / ResizeObserver / IntersectionObserver polyfills for AntD 5）+ `test/utils.tsx`（renderWithProviders helper）
  - CI：`.github/workflows/ci.yml` 新增 `backend-test`（postgres service + pytest + Codecov）和 `frontend-test`（vitest + Codecov）两个 job；`.codecov.yml` 双 flag 配置
- **Backend 单元测试**（68 个新 tests）
  - `test_litellm_helpers.py` (17)：resolve_litellm_model 的 OpenAI 兼容 / 原生 provider / 边界条件
  - `test_system_params.py` (15)：get / get_int / get_decimal / cache / invalidate / get_all
  - `test_approval.py` (15)：规则匹配 / 阶段推进 / 拒绝短路 / 代理人 / 授权检查 / fallback
  - `test_notifications.py` (11)：创建 / 订阅 mute / 去重窗口 / 列表 / count_unread / mark_read
  - `test_cerbos_client.py` (10)：Cerbos fallback 等价性 × 8 种 role×resource + 边界
- **Frontend 单元测试**（32 个新 tests）
  - `stores/notification.test.ts` (5)：refresh / markRead / markAllRead
  - `components/ui/*.test.tsx` (13)：StatCard / Section / PageHeader / EmptyState
  - `theme/ThemeProvider.test.tsx` (7)：mode 持久化 / matchMedia / data-theme / 越界 throw
  - `test/smoke.test.ts` (3)：jsdom 基础验证
- **Dashboard 月环比趋势**
  - `GET /api/v1/dashboard/metrics?compare_to=last_month|last_week`（新 endpoint）
  - 4 个 StatCard 显示 ↑/↓ 箭头 + 百分比 delta（direction=flat 时不显示）
  - 额外 `expiring_contracts_30d` + `price_anomalies_pending` 计数
- **Cerbos 策略引擎集成**
  - `docker-compose.yml` 新增 `cerbos` sidecar（`ghcr.io/cerbos/cerbos:0.40.0`，disk-based policy + watchForChanges 热更新）
  - 4 个 resource policy YAML（`purchase_requisition` / `purchase_order` / `payment_record` / `invoice`），与原 `FIELD_PERMISSIONS` dict 1:1 等价
  - `backend/app/core/cerbos_client.py`：async HTTP client + graceful fallback（Cerbos 不可达时降级到静态 dict）
  - `api/v1/authz.py`：field-manifest 端点切换到 Cerbos check_field_access
  - `services/search.py`：搜索 meta 过滤切换到 filter_dict_via_cerbos

### 改进

- **Frontend bundle 代码分割**
  - 16 个页面组件改用 `React.lazy` + `<Suspense>` 包裹
  - `vite.config.ts` 加 `manualChunks`（antd / react-vendor / router / i18n / dayjs / axios / zustand）
  - 主 chunk `index.js`：**1,531 KB → 42.8 KB (-97%)**；路由导航按需加载 9-15 KB 页面 chunk
  - 补上遗漏的 `/notifications` 路由
- **暗色模式对比度**
  - Playwright 截图验收 Dashboard / Admin / PODetail × light/dark（5 张归档）
  - `tokens.ts`：dark border 提亮 (`#2F2B27→#3A3632` / `#4F4943→#5A544E` / `#6F6861→#7A7369`)
  - `tokens.ts`：dark text secondary/tertiary 提亮 (`#CFCAC5→#D5D0CB` / `#8F8881→#9E9790`)
  - `antdTheme.ts`：dark Table borderColor 改用 border token（不再硬编码 neutral[800]）
- **水獭 SVG 插画升级**
  - 3 张 geometric placeholder 替换为详细矢量水獭（head/ears/face/nose/eyes/mouth/arms/paws/feet/tail + 场景道具）
  - `otter-empty`：睡觉水獭 + Zzz + 漂浮几何图形
  - `otter-search`：举放大镜水獭 + 问号
  - `otter-welcome`：挥手水獭 + 闪烁粒子
  - 保留 CSS var 主题适配，每张 <3 KB
- **主题切换图标**
  - AppLayout：emoji（☀️🌙💻）→ AntD `SunOutlined` / `MoonOutlined` / `DesktopOutlined`

### 修复

- **LiteLLM provider 路由**：OpenAI 兼容 vendor 的 model_string 含斜杠时被 LiteLLM 误判为 HuggingFace repo。新增 `resolve_litellm_model()` 自动补 `openai/` 前缀（DB 值不变）
- **Embedding modality 分派**：`test_ai_model_connection` 对所有 modality 都调 `acompletion`。改为按 `AIModel.modality` 分派（embedding → `aembedding`）
- **Embedding encoding_format=null**：LiteLLM 默认传 `encoding_format=None`，Modelverse 严格 schema 拒绝。改为显式传 `"float"`
- **前端 API 客户端 URL 双重前缀**：`admin-system-params.ts` / `notifications.ts` / `search.ts` 共 10 处 `/api/v1/` 冗余导致 404
- **Admin LLM 表单**：新增 OpenAI 兼容配置 Alert 引导 + Provider/Model String 字段 help 文案
- **版本号同步**：v0.5.0 发布时遗漏的 4 处 version drift 对齐

### 测试数据

| | v0.5.0 | v0.6.0 | Δ |
|---|---|---|---|
| Backend tests | 3 | **71** | +68 |
| Frontend tests | 0 | **32** | +32 |
| **Total** | **3** | **103** | **+100** |
| Backend coverage | N/A | **57%** | — |
| approval.py | 0% | **87%** | — |
| notifications.py | 0% | **53%** | — |
| system_params.py | 0% | **50%** | — |
| litellm_helpers.py | N/A | **100%** | — |
| Main JS chunk | 1,531 KB | **42.8 KB** | **-97%** |

---

## [v0.5.2] — 2026-04-22

Hotfix：修复 OpenAI 兼容第三方 Embedding 模型 test-connection 400 错误。

### 修复

- **LiteLLM aembedding payload `encoding_format=null` 兼容性**：某些 OpenAI 兼容 vendor（如 Modelverse）对 `encoding_format: null` 做严格 schema 校验会返回 `400 invalid embeddings request parameters`。
  - LiteLLM 底层调用 `openai.embeddings.create` 时会默认传 `encoding_format=None`，部分 vendor 不接受
  - 诊断：同样的 payload 去掉 `encoding_format` 字段或设为 `"float"` 都正确返回
  - 修复：在 `admin.py::test_ai_model_connection` 的 embedding 分支显式传 `encoding_format="float"` 绕开
- **实测证据**：
  ```
  Qwen3 Embedding 8B (Modelverse)
  Before: HTTP 400 "invalid embeddings request parameters"
  After:  HTTP 200, dim=4096, 1925ms ✅
  ```

### 内部

- 修复了 v0.5.1 CHANGELOG 中记录为"待 Wave 1 A3-1 跟进"的问题，已提前解决
- 版本号 bump 到 0.5.2

---

## [v0.5.1] — 2026-04-22

Hotfix 补丁：修复 LLM 接入的 3 类路由问题 + 前端 API 客户端路径 bug。无 schema 变更、无破坏性改动。

### 修复

- **LiteLLM provider 路由**：用户配置 OpenAI 兼容第三方服务（Modelverse / DeepSeek / GLM / Together AI 等）时，如果 `model_string` 含斜杠（如 `zai-org/glm-4.7`）会被 LiteLLM 误判为 HuggingFace repo，抛 `BadRequestError: LLM Provider NOT provided`。
  - 新增 `backend/app/core/litellm_helpers.py::resolve_litellm_model()`：根据 `provider` 字段（`openai` / `openai-compatible` / `deepseek` / `modelverse` / `glm` 等白名单）自动在调用时补 `openai/` 前缀
  - DB 存储值保持不变（用户原样填的 model id），只在调用 LiteLLM 前 normalize
  - 覆盖两个调用点：`admin.py::test_ai_model_connection`、`services/ai.py::_call_litellm_stream`
  - 17 个新单元测试（`tests/unit/test_litellm_helpers.py`）
- **Embedding modality 分派**：`test_ai_model_connection` 之前对所有 modality 都调 `litellm.acompletion`，Embedding 模型直接报 `model does not support Chat Completions API`。
  - 按 `AIModel.modality` 分派：`embedding` → `litellm.aembedding(input=["ping"])`；其余 → `acompletion(messages=...)`
  - 返回 vector 维度作为 `model_response`（例：`[embedding] dim=1024`）
- **前端 API 客户端 URL 双重前缀**：4 处文件把 `/api/v1/` 硬编码进相对路径，而 axios client 的 `baseURL` 已经是 `/api/v1`，导致浏览器实际请求 `/api/v1/api/v1/...` → 404
  - `admin-system-params.ts`（4 处）：修复"系统管理 → 系统参数"白屏 "Failed to fetch system parameters"
  - `notifications.ts`（5 处）：修复 NotificationBell 加载失败 + 通知中心空白
  - `search.ts`（1 处）：修复 Header 全局搜索 404
  - `pages/Payments.tsx` 与 `api/index.ts` 的原生 `fetch('/api/v1/...')` 保留（需要完整路径，非 bug）
- **前端 UI 引导**：Admin Drawer"新增 / 编辑 LLM 模型"顶部加 `<Alert>` 块，说明 OpenAI 兼容服务的 4 项填写约定；Provider / Model String 字段各加 help 文案解释自动补前缀行为

### 实测证据

```
$ curl -X POST /api/v1/admin/ai-models/{id}/test-connection
  GLM 4.7         → success=true 2691ms
  GLM 5V Turbo    → success=true 766ms
  Kimi K2.6       → success=true 920ms
  Qwen3 Embedding → success=false（端点切对了，Modelverse 返 400 param_error，vendor-specific 载荷问题，Wave 1 A3-1 跟进）
```

### 已知仍待处理

- Qwen3 Embedding 8B 在 Modelverse 端点返 `Invalid param: invalid embeddings request parameters` — 端点路由正确但 vendor 要求特定 payload 格式。预留给 v0.6 A3-1。
- 前端 bundle 还是 1.5 MB（B1 代码分割在 v0.6）

### 内部

- 版本号统一 bump（`pyproject.toml` / `package.json` / `deploy/.env` / `config.py::app_version`），修复 v0.5.0 发布时遗漏的 4 处同步点

---

## [v0.5.0] — 2026-04-21

独立运行体验打磨：在不对接任何外部组件（飞书 / ADFS / 云账单）的前提下，把系统本身的功能完备性 + UI 体验打磨到生产可用水平。

### 新增

- **设计系统**：水獭棕 `#8B5E3C` 品牌色 10 级 + 冷暖灰中性 12 级 + 浅色 / 暗色双主题，系统偏好跟随 + 手动切换（localStorage 持久化）
- **UI 原语**：`PageHeader` / `StatCard` / `Section` / `EmptyState` 4 个可复用组件
- **水獭 SVG 插画**：`otter-empty` / `otter-search` / `otter-welcome`（`currentColor` 适配暗色）
- **响应式布局**：`AppLayout` 在 `lg` 断点切换到 Drawer 模式，移动端审批 / 查看流畅
- **通知系统**：`Notification` + `NotificationSubscription` 模型，审批 / 合同到期 / 价格异常自动推送
  - Header 铃铛 + 未读徽章 + 下拉抽屉
  - 独立通知中心页（Inbox + 订阅设置）
  - 审批任务分派时 → 推送给分派人；审批决定 → 推送给提交者
- **系统参数**：14 个硬编码阈值从代码搬到 DB，Admin 控制台"系统参数"Tab 可编辑
  - 涉及：审批金额、JWT/刷新令牌有效期、SKU 基准窗口 / 异常阈值、合同提醒窗口、上传限制、分页默认、审计回溯天数
  - 每个参数带 min/max 边界校验 + 单位 + 中英描述 + 重置到默认
- **统一全文搜索**：`GET /api/v1/search?q=&types=` 一个端点覆盖 7 张业务表
  - PR / PO / 合同 / 合同文档 / 发票 / 供应商 / 物料
  - pg_trgm + tsvector（`simple` 配置）+ GIN 索引
  - Header 全局搜索框（Cmd/Ctrl+K 聚焦，300ms 防抖，按类型分组结果）
  - 独立搜索结果页 `/search`
- **多级审批 DSL**：`ApprovalRule` 表按 `biz_type + 金额区间 + stages` 路由串签
  - 种子规则：`< ¥100k → dept_manager`（单阶段）· `≥ ¥100k → dept_manager → procurement_mgr`（两阶段串签）
  - 前一阶段通过后自动激活下一阶段；任一阶段拒绝后续阶段置 `skipped`
  - 管理员可 API / UI 增改规则
- **审批代理人**：`ApproverDelegation` 表支持出差临时委托
  - 时间段 + 原因 + 软撤销
  - 审批路由时自动检测活跃委托并转发任务
- **主数据 CRUD**：Supplier / Item / Company / Department 的增删改查
  - Department 支持 `parent_id` 树层级 + 循环检测
  - 每次写操作记入审计日志
  - Supplier/Item CUD 开放给 admin + procurement_mgr；Company/Department 仅 admin
- **PDF 导出（PO → 供应商签章版）**：`GET /api/v1/purchase-orders/{id}/export/pdf`
  - reportlab + STSong-Light CID 中文字体（无系统依赖）
  - 品牌色表头 + 斑马纹行项目 + 合计行 + 条款 + 签章位
- **Excel 导出（付款记录 → 财务）**：`GET /api/v1/payments/export/excel?po_id=&status_filter=`
  - openpyxl 生成 XLSX，冻结首行 + auto_filter + 合计行 + 品牌色样式
- **打印样式**：`@media print` 自动隐藏 Header / Sider / 按钮 / 分页，表格分断友好，链接附外部 URL
- **移动端响应式**：`@media (max-width: 576px)` StatCard 1 列 + 表格横滚 + 字号缩放 + Drawer 全屏 + 粘底操作栏
- **运维脚本**（`deploy/scripts/`）：
  - `health.sh` — 容器 / DB / API 健康检查（人读或 `--json`）
  - `backup.sh` — pg_dump + media tar 组合归档 + manifest.json
  - `restore.sh` — 双重确认的恢复（`--yes-i-know` + TTY `YES`）
  - `upgrade.sh` — 预检 → 备份 → 构建 → 迁移 → 健康检查（失败自动回滚）
  - `logs.sh` — `docker compose logs` 便捷包装

### 变更

- **用户手册配色**：mkdocs theme 从 `teal/orange` 改为 `brown/deep-orange` 对齐品牌
- **文档主题**：新增 `docs/user-manual/assets/mica.css` 精调水獭棕主色
- **字体**：前端全站使用 Inter（`@fontsource/inter` 自托管），代码字体 JetBrains Mono
- **Admin 控制台**：从 6 个 Tab 扩展到 7 个（新增"系统参数"）；原"系统参数"Tab 改名为"系统信息"
- **AppLayout**：Header 高度 56px，左有 Logo + 响应式菜单切换，中间搜索槽，右有通知铃铛 + 语言 + 主题切换 + 用户下拉

### 修复

- **Pydantic v2 递归类型**：`JSONValue` 从 `TypeAlias` 递归定义改为 `Any`，解决启动时 `RecursionError`
- **SQLAlchemy Enum 反序列化**：`SystemParameterCategory` + `NotificationCategory` 补齐 `values_callable=lambda e: [m.value for m in e]`，正确映射 DB 里的小写字符串

### 迁移

- `0002_notifications` — notifications + notification_subscriptions 表
- `0003_system_parameters` — 14 行 seed 业务参数
- `0004_fts_trigram` — 7 张表的 `search_vector` 生成列 + pg_trgm 扩展 + GIN 索引
- `0005_approval_rules_dsl` — approval_rules + approver_delegations 表 + 2 行 seed 规则 + `approval_tasks.meta` 列
- `0006_schema_additions` — `departments.parent_id` 与 `suppliers.notes` 列

### 依赖

- `reportlab>=4.2.5`（PDF 生成，含 STSong-Light CID 中文字体）
- `openpyxl>=3.1.5`（Excel 生成）
- `@fontsource/inter`（前端自托管 Inter 字体）
- `zustand`（轻量状态管理，用于通知 store）

### 文档

- 新增 [ADR 0002](docs/adr/0002-search-pg-trgm-over-zhparser.md)：全文检索选型决策
- 新增 [ADR 0003](docs/adr/0003-system-parameters.md)：系统参数集中配置决策
- 新增 [deploy/scripts/README.md](deploy/scripts/README.md)：运维脚本使用 + cron 示例 + 故障排查
- 新增 本 CHANGELOG

---

## [v0.4.2] — 2026-04-21（早些时候）

### 新增

- **SKU 行情库**：`GET /api/v1/sku/benchmarks/{item_id}` 返回 90 天基准价（avg / median / stddev / min / max / sample_size）
- **价格异常检测**：录入新价格时若偏离 ±20% 自动创建 `SKUPriceAnomaly` 记录（warning）或 ±40%（critical）
- **价格趋势**：`GET /api/v1/sku/trend/{item_id}` 返回近 180 天的价格点
- **合同附件**：PDF/OFD/XML/图片多格式上传，SHA-256 去重，一次性下载 token
- **合同 OCR 全文检索**：4 级分层抽取（PDF 结构化 / PDF OCR / OFD / LLM Vision）
- **合同到期提醒**：`GET /contracts-expiring?within_days=30`
- **发票详情页**：统一展示 PO 关联 / 产品行 / 金额 / 备注 / OCR 原文

### 修复

- 多处字段级权限边界修正

---

## [v0.4.1] — 2026-04（更早）

### 新增

- **管理员控制台前端**：LLM 模型 / AI 场景路由 / 用户管理 / AI 日志 / 审计日志 6 个 Tab（v0.5 新增第 7 个）
- **发票附件 + AI 抽取**：6 级分层策略（XML 99% 置信度 / PDF / OFD / 图片 OCR / LLM Vision 兜底 / 人工复核）

---

## [v0.4.0] — 2026-03

### 新增

- **LLM 网关**：LiteLLM SDK 接入，支持 OpenAI / DeepSeek / 通义 / 豆包 等多家模型
- **表单 AI 润色**：PR 标题 / 业务理由智能补全
- **字段级 + 行级权限**：按角色差异化可见字段 + 业务数据过滤

---

## [v0.3.0] — 2026-02

### 新增

- **审批引擎**：单级阈值路由（< ¥100k → 部门负责人；≥ ¥100k → 采购经理）
- **Walking Skeleton**：`docker compose up -d` 3 分钟启动端到端采购主线

---

## [v0.1.0 / v0.2.0] — 2025-12 ~ 2026-01

### 新增

- 采购申请 → 采购订单 → 合同 → 交货 → 付款 → 发票 的完整业务主线骨架
- 多公司主体 + 多币种预留
- 中英双语 i18n 框架
- PostgreSQL + SQLAlchemy 2 async + Alembic 迁移基础设施
- Docker Compose v2 + Nginx 部署骨架

---

## 版本路线（规划中）

### v0.6（下一迭代）

- 飞书集成（消息通知 + 审批卡片联动，需 App ID/Secret）
- 单元测试覆盖 + GitHub Actions CI 流水线
- 真实 LLM 模型接通演示
- 批量导入 Excel（供应商 / 物料 / 历史报价）

### v0.7+

- Cerbos sidecar 化（字段级 authz 独立为策略引擎）
- PostgreSQL zhparser 中文分词（升级当前 pg_trgm 方案）
- PO 成交价自动回填 SKU 价格库
- 多级审批 DSL 可视化编辑器
- 合同版本管理 / 电子签 / 续签流

### 按需

- ADFS SAML 真实对接（骨架已就绪）
- 云服务商账单自动生成月度 PO
- 前端 bundle 代码分割

---

**最后更新**：2026-04-21 · **维护人**：helixzz
