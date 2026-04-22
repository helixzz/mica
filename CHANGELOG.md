# Changelog

All notable changes to Mica will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased] — v0.6.0-dev.4 (2026-04-22)

**状态**：v0.6 开发中。A2-B4 + B1 + B5 + 补缺的路由。

### 新增

- **A2-B4 approval service 单元测试**（15 tests）
  - 小额/大额规则匹配、单/双阶段路由
  - 阶段推进（第一阶段 approve → 第二阶段 pending）
  - 拒绝短路（后续 waiting tasks → skipped）
  - 返回操作（同拒绝类似）
  - 代理人委托（delegation 激活时 assignee 切到 delegate）
  - 未授权用户不能 act_on_task
  - 非法 action 返回 422
  - count_pending_for_user / list_pending_tasks / get_instance_for_biz
  - 无匹配规则时回退到 legacy threshold 路径
  - **coverage: 42% → 87%**（+45!!）

- **B5 Dashboard trend**
  - 后端新增 `GET /api/v1/dashboard/metrics?compare_to=last_month|last_week`
  - 新模块：`backend/app/api/v1/dashboard.py`
  - 返回 4 个 trend 指标：`pr_count` / `po_count` / `po_total_amount` / `pending_approvals`（每个带 current/previous/direction/delta_pct）
  - 额外两个简单计数：`expiring_contracts_30d` / `price_anomalies_pending`
  - 前端 `api/index.ts` 加 `getDashboardMetrics()` + `DashboardMetrics` / `TrendInfo` 类型
  - `Dashboard.tsx` 的 4 个 StatCard 接入 trend（direction=flat 时不显示，避免"没变化"也画个箭头）

- **B1 Bundle code splitting**
  - `routes/index.tsx` 改用 `React.lazy` + `<Suspense fallback={<Spin/>}>` 包裹 **16 个页面**
  - `vite.config.ts` 加 `manualChunks`：antd / react-vendor / router / i18n / dayjs / axios / zustand
  - 顺便补上 `/notifications` 路由接到 NotificationCenter（之前缺）
  - **Build 结果**：
    - main `index.js`: **1,531 KB → 42.8 KB** (-97%)
    - 页面 chunks: Dashboard 9.6KB, Admin 14.4KB, PODetail 15KB 等
    - vendor chunks: antd 1.14MB / react-vendor 142KB / axios 38KB / i18n 60KB
  - `chunkSizeWarningLimit` 提到 1500 适配 antd chunk 大小

### 测试总数

- Backend: 46 → **61 tests pass**（+15 approval）
- Frontend: 32 tests pass（不受 B1 改动影响）
- **总计 93 tests, all green**
- Backend coverage: 55% → **57%**
  - approval: 42% → 87%
  - 整体测试基础设施已非常稳固

---

## [Unreleased] — v0.6.0-dev.3 (2026-04-22)

**状态**：v0.6 开发中。Wave 1 A2-F4 收尾：ThemeProvider hook 测试。

### 新增（相对 dev.2）

- **Wave 1 A2-F4**：7 个 ThemeProvider + useTheme 测试
  - 默认 `'system'` 模式
  - localStorage 读取 + 持久化
  - `setMode` 更新 `data-theme` attr
  - `matchMedia` prefers-dark / prefers-light 正确分派
  - `useTheme()` 在 Provider 外调用时 throw

### 测试总数

- Backend: 46 tests pass（无变化）
- Frontend: 25 → **32 tests pass**
- **总计 78 tests, all green**

### Wave 1 状态

✅ **Wave 1 全部完成**（除 A2-B4 approval 单元测试推迟到下一批；approval 已通过 walking_skeleton 获得 42% 覆盖）

---

## [Unreleased] — v0.6.0-dev.2 (2026-04-22)

**状态**：v0.6 开发中。在 dev.1 基础上补充 services 单元测试，覆盖率阶梯上升。

### 新增（相对 dev.1）

- **Wave 1 A2-B3 (system_params)**：15 个单元测试覆盖 `SystemParamsService`（get / get_int / get_decimal / get_int_or / cache / invalidate / get_all / get_param / 边界条件 + 模块单例）。覆盖率 34% → **50%**。
- **Wave 1 A2-B5 (notifications)**：11 个单元测试覆盖核心 notification service（create / mute subscription / callable title / recent dedupe / list / count_unread by_category / mark_read by ids + all）。覆盖率 26% → **53%**。
- **`seeded_db_session` fixture**：在 `conftest.py` 新增。为需要 seed users/suppliers/items 的 service 测试提供已 seed 的 savepoint 隔离 session。同时清理 legacy `seeded_client` 留下的 notifications 污染，避免测试间泄漏。

### 覆盖率进展（backend）

| 模块 | dev.1 | dev.2 | Δ |
|---|---|---|---|
| `core/litellm_helpers.py` | 100% | 100% | — |
| `services/approval.py` | 20% | 42% | +22 |
| `services/notifications.py` | 26% | **53%** | +27 |
| `services/system_params.py` | 34% | **50%** | +16 |
| **Total** | 54% | **55%** | +1 |

（注：approval 提升来自 walking_skeleton 用 seeded_client 走完整端到端路径；专门的 unit 测试作为 A2-B4 待补）

### 测试总数

- Backend: 35 → **46 tests pass** (0.02s-3.5s runtime)
- Frontend: 25 tests pass（无变化）
- **总计 71 tests, all green**

---

## [Unreleased] — v0.6.0-dev.1 (2026-04-22)

**状态**：v0.6 开发中。首个 dev 发布：测试基础设施 + 首批单元测试 + CI 覆盖率上传 + UI 小改。

### 新增

- **Backend 测试基础设施 (A2-B1)**
  - `tests/conftest.py` 完全重写：
    - 删除 deprecated `event_loop` session fixture
    - `pyproject.toml` 加 `asyncio_default_fixture_loop_scope = "session"` + `asyncio_default_test_loop_scope = "session"`
    - `db_session` fixture 用 **SAVEPOINT rollback pattern**（`join_transaction_mode="create_savepoint"`）：`session.commit()` 在测试中成为 SAVEPOINT release，outer transaction 保证 rollback → 零状态泄漏
    - 新 `client` fixture：FastAPI `app.dependency_overrides[get_db]` 替代旧 monkeypatch
    - `seeded_client` 保留为 legacy（带 deprecation 说明）
    - `test_engine` 改用 `alembic upgrade head`（subprocess 规避 asyncio 嵌套 loop 冲突），确保 migrations 里的 seed data（system_parameters、approval_rules 等）也就位
  - pytest-asyncio 依赖 bump 到 `>=0.26.0`
- **Backend 测试补充**
  - `tests/unit/test_litellm_helpers.py`：17 个单元测试覆盖 `resolve_litellm_model`（OpenAI 兼容白名单 / 原生 provider 前缀 / 边界条件）
  - walking skeleton 整体重跑绿（20/20 pass）
- **Frontend 测试基础设施 (A2-F1)**
  - 依赖：`vitest` + `@testing-library/react` + `@testing-library/jest-dom` + `@testing-library/user-event` + `jsdom` + `@vitest/coverage-v8`
  - 新建 `vitest.config.ts`（jsdom + v8 coverage）
  - 新建 `src/test/setup.ts`：`matchMedia` / `ResizeObserver` / `IntersectionObserver` polyfills（AntD 5 依赖）
  - 新建 `src/test/utils.tsx`：`renderWithProviders` helper（ConfigProvider + MemoryRouter + I18nextProvider）
  - package.json scripts：`test` / `test:watch` / `test:coverage`
- **Frontend 测试补充**
  - `src/stores/notification.test.ts`：5 个测试覆盖 refresh / markRead / markAllRead + 空 ids 防御 + API 失败处理
  - `src/components/ui/*.test.tsx`：StatCard / Section / PageHeader / EmptyState 共 17 个 render 测试
  - 初始 coverage baseline：notification store 92% / ui primitives 79%
- **CI 扩展 (A2-CI)**
  - `.github/workflows/ci.yml` 新增 2 个 job：
    - `backend-test`：postgres service container + pytest + xml coverage → Codecov (`flags: backend`)
    - `frontend-test`：vitest + lcov coverage → Codecov (`flags: frontend`)
  - 新建 `.codecov.yml`：ignore patterns（migrations / tests / __init__.py / dist / assets / i18n）+ 双 flag 配置

### 改进

- **B2 主题图标 AntD 化**：`AppLayout.tsx` 主题切换按钮替换 emoji（☀️🌙💻）→ AntD `SunOutlined` / `MoonOutlined` / `DesktopOutlined`，并改用 Button `icon` prop 惯用法

### 内部

- 版本号 bump 到 0.6.0-dev.1（进入 v0.6 开发期，首个 dev tag）
- `v0.6-work-plan.md` 进度更新：A2-B1 / A2-F1..F3 / A2-CI1..3 / B2 标记完成
- `tests/` 目录结构：`tests/unit/` 子目录（pure unit tests）vs 根 `tests/` 下 integration tests

### 🚧 进行中 / 下一步

- Wave 1 剩余：services 单元测试（system_params / approval / notifications）→ 目标 backend coverage 从当前 54% 提升到 70%+
- A3-1（LLM UI 补强 + feature routing）
- A4（Cerbos sidecar）
- B1 / B3 / B4 / B5

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
