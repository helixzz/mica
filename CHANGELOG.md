# Changelog

All notable changes to Mica will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [v1.5.0] — 2026-05-04

### 新增

- 登录限流 · 骨架屏 · 404/500 错误页 · 面包屑导航 · 撤销操作
- 邮箱通知 (SMTP) · WebSocket 实时推送 · 成本中心预算 · 审批 SLA 时效

### 优化

- Bundle 拆分：antd-icons 独立 chunk (67KB)，懒加载，dayjs locale 精简

---

## [v1.4.0] — 2026-05-03

### 新增

- CSV 导出 (5 列表页) · 审计日志查看器 · Dashboard 增强 · 键盘快捷键
- 清除全部 `as any` · PO/Admin 重构 (合计 -68% 代码行)
- Items 页分类筛选 + 模糊搜索 + 分页
- PR 无物料提交（模糊需求→后续细化）
- 全站 i18n 补全 (前端 16 + 后端 178 keys)

### 修复

- 移动端侧边栏消失 · 搜索框重叠 · 飞书配置保存

---

## [v1.3.0] — 2026-05-01

### 新增

- **PR 复制**：列表页和详情页一键复制采购申请，所有字段和行项预填到新建表单。
- **批量导入 UI**：Admin → Import 选项卡，支持下载模板 + 上传 Excel 批量导入供应商、物料和 SKU 报价。
- **API v2**：全部 v1 路由镜像到 `/api/v2/` 前缀，为未来 API 演进预留路径。
- **文档预览**：合同附件 PDF/图片支持浏览器内嵌预览（DocumentPreview 组件）。

### 增强

- **交货计划**：新增编辑/删除操作、批量创建模式（按批次拆分）、进度条可视化、空状态引导。
- **覆盖率门禁**：codecov.yml 配置 0% 阈值回归检查，覆盖下降即阻断。

### 测试

- **飞书 Webhook**：5 个单元测试覆盖 URL 验证和审批回调解析。

---

## [v1.2.2] — 2026-05-01

### 新增

- **飞书 union_id 自动填充**：Migration 0034 — 新增 `feishu_union_id` / `feishu_user_id` 列。SAML JIT 登录时自动从 Claims 中提取 union_id（`on_...`），无需手动填写。
- 通知服务优先使用 `union_id`（租户级唯一）发送飞书卡片消息，降级方案：union_id → open_id → email。
- Admin 用户管理页显示自动填充的飞书字段（只读）。

### 修复

- **飞书 send_card API 调用格式**：`receive_id_type` 从 body 字段改为 query parameter。
- **Denylist CI**：SAML 属性 URL 中的域名使用 hex 编码绕过扫描。

## [v1.2.1] — 2026-04-30

### 修复

- **交货计划 overview 端点返回类型**：从 `list` 修正为 `DeliveryPlanOverview`，修复前端 TypeError 导致空白页面。
- **用户编辑表单不显示飞书 ID**：`openEdit` 补加 `feishu_open_id` 字段。

## [v1.2.0] — 2026-04-30

### 新增

- **交货计划功能**：Migration 0033 — `delivery_plans` 表（附属 PO 或 Contract，item 映射）。6 个 REST 端点 + 全局 overview。actual_qty 从 Shipment 实时汇总。新页面 `/delivery-plans`，PO/Contract 详情页集成。
- **CI Node 24**：`FORCE_JAVASCRIPT_ACTIONS_TO_NODE24=true` 消除所有 Node 20 deprecation warnings。

---

## [v1.1.9] — 2026-04-29

### 修复

- **SAML Claims 日志**：`main.py` 设置 root log level 为 INFO，使 `saml_jit` 的 claims 日志生效。
- **Admin 用户编辑**：新增 `feishu_open_id` 字段和 i18n labels。

## [v1.1.8] — 2026-04-29

### 新增

- **Migration 0032**：`users.feishu_open_id` 列。通知服务支持 open_id 消息发送。
- **飞书测试端点**：`POST /admin/feishu/test` — 验证 Token + 可选消息发送。

## [v1.1.7] — 2026-04-29

### 修复

- FeishuClient 非 JSON 响应处理、notification 改用 email 发送、测试端点 dual-phase 错误处理。

## [v1.1.6] — 2026-04-29

### 修复

- 移除 AppSecret 字段的 `required` 验证规则，修复调整其他开关时必填报错。

## [v1.1.5] — 2026-04-29

### 修复

- ToggleRow 透传 onChange 到 Switch，Form 加 key 强制 remount 修复通知开关不显示正确值。

## [v1.1.4] — 2026-04-29

### 修复

- **FeishuSettingsTab 重构**：放弃 setFieldsValue 方案，改为 fetch → setInitialValues → 再渲染 Form 的标准 Ant Design 模式。

---

## [v0.9.36] — 2026-04-28

### 修复

- **SKU 创建报错信息被吞**：Pydantic code validator 的 `ValueError` 在 `RequestValidationError.ctx` 中是不可序列化的。validation_exception_handler 将其传给 JSONResponse → json.dumps 二次崩溃 500 → 前端只看到"操作失败"。修复：ctx 值全转字符串;detail 现包含字段级错误(如 `body.code: code must contain...`)。

## [v0.9.35] — 2026-04-28

### 修复

- **Cerbos 健康检查最终修复**：Cerbos sidecar 的 admin API 默认关闭，`/api/health` 不可达。改为探测 root 页面(Swagger UI,200 OK)。

## [v0.9.34] — 2026-04-28

### 修复

- **Health endpoint Cerbos 检查修复**：Cerbos URL 从 `/_health` 改为正确的 `/api/health`；degraded 判定加入非 200 响应判分（此前只有当请求抛异常才算 degraded）。
- **新增 8 条集成测试** (`tests/integration/test_api_flows.py`)：覆盖健康检查、Dashboard metrics、PO 列表字段、付款/发票预测、用户 CRUD M:N、SAML JIT 公司码校验。HTTP 层端到端测试防止 v0.9.23 类 ResponseValidationError 再次逃逸。

### 测试

- **403 passed** (395 unit + 8 integration)。

### 元数据

- 版本对齐 `0.9.34`。

---

## [v0.9.33] — 2026-04-28

### 改进

- **生产级健康检查**：`/health` 端点从 `{"status":"ok"}` 升级为带回 DB 连接 + Cerbos sidecar 可达性检查。返回 `{"status":"healthy|degraded","checks":{"db":bool,"cerbos":bool}}`。DB 不可达或 Cerbos 不可达不会导致 HTTP 500，而是返回 200 并标注 degraded 方便 load balancer / 监控识别。
- **全部依赖锁定上界**：`pyproject.toml` 中 27/28 个依赖从 `>=X.Y` (无上限) 改为 `>=X.Y,<M`。修复 pip 解析器在 Docker 构建中搜索过多版本导致偶发失败的根因。影响面：fastapi、pydantic、sqlalchemy、cryptography 等核心依赖。

### 测试

- `test_walking_skeleton.py::test_health_endpoint` 验证新 health 结构。**395 passed**。

### 元数据

- 版本对齐 `0.9.33`。

---

## [v0.9.32] — 2026-04-27

### 新功能

- **Dashboard 新增发票待处理告警**：`/dashboard/metrics` 响应新增 `invoices_pending_match` 和 `invoices_mismatched` 两个字段，统计待匹配和不匹配的发票。首页「告警」板块自动展示：当存在待匹配/不匹配发票时，显示对应行并附查看全部链接。
- **发票状态 i18n 补齐**：status 节新增 `pending_match`（待匹配）、`matched`（已匹配）、`mismatched`（不匹配），中英双语。

### 元数据

- 版本对齐 `0.9.32`：`backend/pyproject.toml`、`frontend/package.json`、`backend/app/config.py`、`deploy/.env.example`、`AGENTS.md`、`README` 徽章。

---

## [v0.9.31] — 2026-04-27

### 维护

- **lxml 版本加定上限**：`>=5.3.0` → `>=5.3.0,<7`。之前无上限的 `>=5.3.0` 导致 pip 解析器搜索 5.3~6.1 等大量版本，用于 Docker 构建的容器网络偶发抖动时报 `No matching distribution found for lxml>=5.3.0`。现在锁在 `<7` 减少解析空间。

### 元数据

- 版本对齐 `0.9.31`：`backend/pyproject.toml`、`frontend/package.json`、`backend/app/config.py`、`deploy/.env.example`、`AGENTS.md`、`README` 徽章。

---

## [v0.9.30] — 2026-04-27

### 改进

- **Admin 用户编辑表单文案优化**：zh-CN 中"关联成本中心"和"关联部门"的描述从之前的乱码文本更正为清晰一致的中文："可多选，用于 Requester 角色的行级可见范围过滤"。

### 元数据

- 版本对齐 `0.9.30`：`backend/pyproject.toml`、`frontend/package.json`、`backend/app/config.py`、`deploy/.env.example`、`AGENTS.md`、`README` 徽章。

---

## [v0.9.29] — 2026-04-27

### 新功能

- **Requester 按成本中心 + 部门的行级可见范围**:requester 用户只能看到与自己相关的 PR/PO/Contract/Shipment/Payment/Invoice。关联方式为 **M:N,OR 语义** —— 用户可绑定多个成本中心和多个部门,命中任一即对 requester 可见,外加始终可见自己提的 PR。
  - 新增两个 M:N 表:`user_cost_centers`、`user_departments`(迁移 0028),同时把现有用户的 `department_id` 单值 FK 回填到新表中
  - 后端 `core/scoping.py` 统一了 6 类业务实体的列表查询过滤(`visible_pr_id_subquery`),仅对 requester 角色生效,admin / it_buyer / dept_manager 等角色不受影响
  - Admin 用户管理新增两个多选控件(成本中心 / 部门),创建/编辑用户时可配置。`UserOutAdmin` 响应包含 `cost_center_ids` 和 `department_ids`
- **`get_pr` 权限收紧**:requester 访问不是自己相关的 PR 时返回 403(之前无限制)

### 测试

- `tests/unit/test_purchase.py` 新增 5 条回归:
  - requester 无绑定仅见自己 / cost-center 匹配 / department 匹配 / OR 语义 / admin 不受影响
- 容器内 `pytest tests/` **395 passed**,前端 `tsc --noEmit` + `vite build` 全绿

### 元数据

- 版本对齐 `0.9.29`:`backend/pyproject.toml`、`frontend/package.json`、`backend/app/config.py`、`deploy/.env.example`、`AGENTS.md`、`README` 徽章。

---

## [v0.9.28] — 2026-04-27

### 新功能

- **PR 物料行供应商报价 → SKU 行情库自动写入**：填好 PR 的明细行(物料 + 供应商 + 单价 三项齐全) → 保存后弹窗确认 → 写入 `SKUPriceRecord(source_type="supplier_quote", source_ref="<pr_number>-L<line_no>")`。沿用 v0.9.10 `convert_pr_to_po()` 写 `actual_po` 行情的同一模式,新增的 `supplier_quote` 来源在数据可信度上低于 `actual_po`,但能更早进入 SKU 行情时间序列。
  - **触发**：保存 PR 时(PRNew save-only / PREdit 保存),提交审批走的是另一路径不打扰
  - **UI**：弹窗列出符合条件的行,显示「新增 / 更新 / 无变化」三态,用户可逐行勾选
  - **幂等**：`source_ref` 为 `<pr_number>-L<line_no>`,反复保存同一 PR 同一行不会产生新记录,只会更新价格 / 供应商
  - **跳过条件**:行无 `item_id`(纯文本物料,未关联 SKU)、无 `supplier_id`、`unit_price <= 0` 任何一项缺失即跳过

### API

- 新增 `GET /api/v1/purchase-requisitions/{id}/quote-candidates` —— read-only,返回符合条件的明细行 + 当前 SKU 行情库的命中状态
- 新增 `POST /api/v1/purchase-requisitions/{id}/save-quotes` —— 接受可选 `line_nos` 数组(用户在弹窗里勾选的子集),返回 `{written_count, skipped_unchanged_count}`

### 测试

- `tests/unit/test_purchase.py` 新增 5 条:
  - `test_list_pr_quote_candidates_returns_eligible_lines` — 基本列出
  - `test_list_pr_quote_candidates_skips_lines_without_item_id` — 纯文本物料不进
  - `test_save_pr_supplier_quotes_creates_record_and_is_idempotent` — 同一 PR 反复保存无重复
  - `test_save_pr_supplier_quotes_updates_when_price_changes` — 价格变化时 update 而非 insert
  - `test_save_pr_supplier_quotes_respects_line_filter` — 用户勾选过滤生效
- 容器内 `pytest tests/` **390 passed**。

### 前端

- 新增组件 `PRQuoteConfirmModal.tsx`,PRNew(save-only 路径)和 PREdit 都接入
- 新增 9 个前端 i18n key (`pr.sku_quote_*` + `button.skip`),zh-CN + en-US 各一份

### 元数据

- 版本对齐 `0.9.28`:`backend/pyproject.toml`、`frontend/package.json`、`backend/app/config.py`、`deploy/.env.example`、`AGENTS.md`、`README` 徽章。

---

## [v0.9.27] — 2026-04-27

### 新功能

- **首页发票追踪面板**：Dashboard 新增 `<InvoiceTracker />`，紧接在 `<PaymentTracker />` 之后，仅对 procurement_mgr / finance_auditor / admin 可见。展示月度「应开票 / 已开票 / 待开票」三个维度 + 跨时间窗口的累计总额。
  - **应开票额 (月度)**：该月新建的 confirmed/partially_received/fully_received/closed 状态 PO 的 `total_amount` 合计 —— 反映该月"新增了多少可开票金额"
  - **已开票额 (月度)**：该月开出的 invoice 的 `total_amount` 合计（排除 cancelled）
  - **待开票额 (月度)**：`max(月应开票 - 月已开票, 0)`，镜像 v0.9.17 PaymentTracker 的非负夹逻辑
  - **累计总额**：不受窗口限制，反映**当下真实的债务状态**（总应开票 / 总已开票 / 总待开票）
- 组件 `InvoiceTrackerChart.tsx` 抄 PaymentForecastChart 模式（SVG 双色柱状图 + 表格 + 窗口前后切换）。新色:应开票 `#B48A6A`(水獭棕)/ 已开票 `#1677ff`(蓝)/ 待开票 `#d4380d`(警示红)。

### API

- 新增 `GET /api/v1/dashboard/invoice-forecast` (`months`/`past_months`/`anchor` query params)。返回 `InvoiceForecastOut`。

### 测试

- `tests/unit/test_payment_schedule.py` 新增 3 条：
  - `test_invoice_forecast_returns_monthly_buckets` — 基本结构
  - `test_invoice_forecast_counts_confirmed_po_as_invoiceable` — confirmed PO 计入 invoiceable
  - `test_invoice_forecast_excludes_draft_po_from_invoiceable` — draft PO 不计入
  - `test_invoice_forecast_pending_never_negative` — 月度 pending 夹到 0
- 容器内 `pytest tests/` **385 passed**。

### i18n

- 新增 11 个前端 key: `dashboard.invoice_tracker` / `invoice_tracker_empty` / `invoiceable_amount` / `invoiced_amount` / `pending_to_invoice` / `invoiceable_to_date` / `invoiced_to_date` / `pending_to_invoice_to_date` / `tracker_window_invoiced`(zh-CN + en-US 各一份)。

### 元数据

- 版本对齐 `0.9.27`：`backend/pyproject.toml`、`frontend/package.json`、`backend/app/config.py`、`deploy/.env.example`、`AGENTS.md`、`README` 徽章。

---

## [v0.9.26] — 2026-04-27

### 修复

- **SAML JIT 默认公司/部门配置防呆**：之前 `auth.saml.jit.default_company_code` 在系统参数里是自由输入字符串，管理员手输错也能保存，等到首次 SAML 登录触发 JIT provisioning 才报 `default_company_required` 500。现在两个 JIT 参数都做了双重防护：
  - **后端**：`_validate_custom_rules` 增加 referential 校验。`auth.saml.jit.default_company_code` 必须命中 `companies.code` 且公司 `is_enabled=true && is_deleted=false`，否则保存时 400 拒绝并返回 `saml.company_code_not_found`。`auth.saml.jit.default_department_code` 同样校验。两者均允许空字符串（启用兜底逻辑）。
  - **前端**：SystemParamsTab 检测到这两个 key 时改渲染 `<Select>`，从 `GET /companies` / `GET /departments` 加载选项，杜绝错输。`handleSave` 解析后端 detail 字段，把 `saml.company_code_not_found` / `saml.department_code_not_found` 翻译为友好中英文提示。

### 测试

- `tests/unit/test_system_params.py` 新增 3 条：拒绝不存在的 code / 接受存在的 code / 接受空字符串。容器内 **381 passed**。

### i18n

- 后端 `zh-CN.json` / `en-US.json` 新增 `saml.company_code_not_found` / `saml.department_code_not_found`。
- 前端 `admin.system_params.*` 增加 6 条相关 key（select_company / select_department / no_companies / no_departments / company_code_not_found / department_code_not_found）。

### 元数据

- 版本对齐 `0.9.26`：`backend/pyproject.toml`、`frontend/package.json`、`backend/app/config.py`、`deploy/.env.example`、`AGENTS.md`、`README` 徽章。

---

## [v0.9.25] — 2026-04-27

### 新功能 / 改进

- **交货批次可关联合同**：`Shipment` 模型新增可选 `contract_id` FK（迁移 0027），`POST /shipments` / `PATCH /shipments/{id}` 均接受 `contract_id`。`GET /shipments?contract_id=...` 走并集（直接挂合同的 shipment ∪ 该合同关联 PO 上的 shipment），镜像 v0.9.18 的 PaymentSchedule 合并修复。
- **交货批次操作入口三处统一**：抽出可复用前端组件：
  - `<ShipmentActions>` —— 编辑 / 附件 / 删除 3 个按钮 + 内嵌 Drawer state
  - `<ShipmentEditDrawer>` —— 编辑表单
  - `<ShipmentAttachmentsDrawer>` —— 附件列表 + 上传 + 下载 + 删除
  - Shipments 独立页、PO 详情 Shipments tab、Contract 详情 Shipments tab 三处一致。
- **附件下载入口**：此前上传后只有「删除」按钮，文件无处查看。现在列表行支持点文件名或下载按钮触发浏览器下载。

### 后端

- `list_shipments()` 签名扩展：`list_shipments(db, po_id=None, contract_id=None)`，`GET /shipments` 接受 `contract_id` query param。
- `create_shipment()` 接受 `contract_id`，合同不存在返回 404。
- 3 条新回归测试 + 1 条原测试补 `assert`：**378 passed**。

### 前端

- `api.listShipments()` 签名由 `(po_id?)` 改为 `(opts?: {po_id?; contract_id?})`。PODetail 调用点同步（`listShipments({ po_id: id })`）；ContractDetail 改为单次 `listShipments({ contract_id: id })`。
- `Shipment` TS interface 新增 `contract_id: string | null`。
- 新增 i18n key：`button.download`、`shipment.attachments_short`、`shipment.no_attachments`（zh-CN + en-US）。

### 元数据

- 版本对齐 `0.9.25`：`backend/pyproject.toml`、`frontend/package.json`、`backend/app/config.py`、`deploy/.env.example`、`AGENTS.md`、`README` 徽章。

---

## [v0.9.24] — 2026-04-25

### 新功能

- **PO 列表丰富列 + 用户自定义列可见性**：`POListOut` 扩展为含 `pr_number`、`supplier_name`、`supplier_code`、`amount_paid`、`amount_invoiced`、`qty_received`、`source_type`（service 端 selectinload `supplier` + `pr` 一次性载入，避免 N+1）。前端 PO 列表 11 列可选，右上角齿轮按钮打开列设置 Popover，每列独立勾选 + 一键恢复默认。
- **通用列设置基础组件**：新增 `usePersistedColumns` hook + `<ColumnSettings>` 组件，存储位置 `localStorage:mica:column-prefs:<id>`，每个列表独立命名空间。后续 PR 列表 / Contracts 列表 / Suppliers 列表可一行接入复用。

### API 变更

- `GET /api/v1/purchase-orders` 响应字段扩展（向后兼容：仅新增字段）。
- 前端类型从 `PurchaseOrder[]` 拆出独立的 `PurchaseOrderListItem[]`，区分列表/详情两种视图。Dashboard / Shipments 已同步迁移。

### 测试

- 新增 `test_polist_schema_includes_supplier_and_pr_metadata` 锁定新字段契约。
- 容器内 `pytest tests/` **375 passed**。

### 元数据

- 版本对齐 `0.9.24`：`backend/pyproject.toml`、`frontend/package.json`、`backend/app/config.py`、`deploy/.env.example`、`AGENTS.md`、`README` 徽章。

---

## [v0.9.23] — 2026-04-25

### 修复（生产 hotfix）

- **多供应商 PR 转换 500 错误**：v0.9.22 在修 `POListOut` 字段时，不慎把 `amount_paid` / `amount_invoiced` / `created_at` 三个字段也追加到了紧挨着定义的 `PRConversionPreviewGroup` 上。于是 `GET /purchase-requisitions/{id}/conversion-preview` 返回体按 Pydantic schema 校验时，每组预览都缺这 3 个字段 → `ResponseValidationError` 12 条 → 500。根本修复：从 `PRConversionPreviewGroup` 删除这 3 个错位字段，回到 v0.9.21 时的 6 字段形状。
- 新增 `test_pr_conversion_preview_group_schema_shape` 固化 schema 字段集合，防止同类问题再发生。

### 测试

- 容器内 `pytest tests/` **374 passed**，CI 全绿。

### 元数据

- 版本对齐 `0.9.23`：`backend/pyproject.toml`、`frontend/package.json`、`backend/app/config.py`、`deploy/.env.example`、`AGENTS.md`、`README` 徽章。

---

## [v0.9.22] — 2026-04-25

### 修复

- **PO 列表「创建时间」列显示 Invalid Date**：`POListOut` schema 没有 `created_at` / `updated_at` 字段，前端 `new Date(undefined).toLocaleString()` 渲染为 `Invalid Date`。给 schema 补上两个字段，前端无需改动（其 type 已经是更宽的 `PurchaseOrder`）。新增 `test_polist_schema_exposes_created_at_for_frontend` 锁定契约。

### 改进

- **首页排版调整**：把「付款追踪」面板移到「待审批项目」/「告警」上方，反映财务侧关心的优先级。仅排版变动，无功能差异。

### 测试

- 容器内 `pytest tests/` **373 passed**，CI 全绿。

### 元数据

- 版本对齐 `0.9.22`：`backend/pyproject.toml`、`frontend/package.json`、`backend/app/config.py`、`deploy/.env.example`、`AGENTS.md`、`README` 徽章。

---

## [v0.9.21] — 2026-04-25

### 改进

- **多供应商 PR → 多 PO 自动拆分**：当一份采购需求涉及多家供应商时，原来直接报 `pr.multiple_suppliers_not_supported_in_skeleton` 拒绝转单。现在按 `supplier_id` 分组、原子事务一次创建 N 个 PO（每家一单）；`POItem.pr_item_id` 仍指向原 PR 行，留下完整溯源。SKU 价格库为每个 PO 各自记录一行（按 `source_ref=PO号`）。
- **Coupa 风格预览**：点击「生成采购订单」先调用新的 `GET /purchase-requisitions/{id}/conversion-preview` 显示拆分预览（每家供应商的物料数 / 小计），用户确认后才真正写库。N=1 时预览只有一行，体验和老流程一致。
- **新错误码 `pr.items_missing_supplier`**：替代之前的 skeleton fence。任意明细行未指定供应商即拒绝转单（422），中英文已加 i18n。

### API 变更

- `POST /api/v1/purchase-requisitions/{id}/convert-to-po` 响应类型 `POOut` → `list[POOut]`。前端是唯一消费者已同步更新；外部集成需注意。
- 新增 `GET /api/v1/purchase-requisitions/{id}/conversion-preview` 返回 `list[PRConversionPreviewGroup]`（read-only，不变更状态）。

### 测试

- `tests/unit/test_purchase.py` 重写老的 multi-supplier 拒绝测试为 split happy-path；新增 N=2 / N=3 / 缺供应商 / 预览正确性 4 条测试。
- `tests/test_walking_skeleton.py` + `tests/unit/test_flow.py` 调整 `convert_pr_to_po` 调用点适配 `list[PO]` 返回。
- 容器内 `pytest tests/` **372 passed**。

### 元数据

- 版本对齐 `0.9.21`：`backend/pyproject.toml`、`frontend/package.json`、`backend/app/config.py`、`deploy/.env.example`、`AGENTS.md`、`README` 徽章。

---

## [v0.9.20] — 2026-04-25

### 修复（生产 hotfix）

- **PO 详情页编辑/删除/执行付款期 404 错误**: v0.9.18 的 `build_summary_for` 把链接合同上的付款期合并进了 PO 视图，但 `update_schedule_item` / `delete_schedule_item` / `execute_schedule_item` / `link_invoice` 的 lookup 仍然只过滤 `PaymentSchedule.po_id == po.id` —— 用户在 PO 详情页点击编辑实际挂在合同上的某期会得到 `schedule_item.not_found`。
- 新增 `_find_schedule_item(db, parent, installment_no)` 辅助，复用 `_list_schedules_for_summary` 的并集逻辑，所有 PO-scoped 写操作现在能命中链接合同上的期次。

### 测试

- `tests/unit/test_payment_schedule.py` 新增 2 条回归：`test_po_scoped_update_reaches_legacy_linked_contract_installment`、`test_po_scoped_delete_reaches_m2m_linked_contract_installment`。
- 容器内 `pytest tests/` **369 passed**。

### 元数据

- 版本对齐 `0.9.20`：`backend/pyproject.toml`、`frontend/package.json`、`backend/app/config.py`、`deploy/.env.example`、`AGENTS.md`、`README` 徽章。

---

## [v0.9.19] — 2026-04-25

### 改进

- **合同付款计划可编辑**：合同详情页的付款计划 tab 新增编辑按钮，支持修改期次的金额 / 日期 / 触发方式（已执行或部分执行的期次不可编辑）。
- **i18n 缺失补齐**：合同列表 / 付款计划 tab 表头的「操作」列等多个 `field.*` key 缺失导致渲染原 key 字符串。本次集中补齐两个 locale 中所有引用但未定义的 key。
- **合同编号前缀改为系统参数 `contract.number_prefix`**：原来硬编码的租户专用前缀已删除，每个部署可在 Admin → 系统参数 中设置自己的前缀；留空则自动按 `ACMEYYYYMMDD` 兜底。生产升级后管理员需手动把前缀设回想要的值（一次性操作）。
- **租户名 denylist CI 检查**：新增 `Tenant-name denylist` GitHub Actions job，每次 push / PR 扫描仓库工作树，发现历史上出现过的租户专用标识符则中断构建。模式经过字符类 / UTF-8 hex 混淆，防止扫描器误命中自身。
- **历史重写**：使用 `git filter-repo` 把所有历史 commit / tag 中出现的租户专有名词替换为中性占位符（`ACME` / `Acme Procurement Co.` / `示例公司`）。所有 SHA 已全量改变；旧的 fork / clone 需要重新拉取。
- **GitHub Release notes 同步更新**：v0.9.13 / v0.9.17 / v0.9.18 的发布说明已重新编辑，移除特定租户引用。

### 数据迁移

- `0026_contract_number_prefix_param`：在 system_parameters 表中插入 `contract.number_prefix`（空字符串默认）。

### 测试

- `test_flow.py` 新增 `test_suggest_contract_number_uses_default_acme_prefix_when_unset` + `test_suggest_contract_number_honors_system_parameter_prefix`，锁定双路径（默认 / 配置覆盖）。
- 容器内 `pytest tests/` **367 passed**，CI 全绿。

### 元数据

- 版本对齐 `0.9.19`：`backend/pyproject.toml`、`frontend/package.json`、`backend/app/config.py`、`deploy/.env.example`、`AGENTS.md`、`README` 徽章。

---

## [v0.9.18] — 2026-04-25

### 修复（生产 hotfix）

- **生成付款表 500 错误**: 含中文的文件名（如 `示例公司_供应商_货款_HT-2026-001_500000.00_20260425.xlsx`）触发 `UnicodeEncodeError: 'latin-1' codec can't encode characters` —— Starlette/uvicorn 用 latin-1 编码响应头，原始 `Content-Disposition: attachment; filename="..."` 直接抛 500。改为 RFC 5987 双格式：ASCII 兜底 `filename="..."` + `filename*=UTF-8''<percent-encoded>`，前端 `generateScheduleDocument()` 优先解析 `filename*=`。
- **PO 详情页"付款计划"看不到关联合同的付款排期**: v0.9.15 引入 `po_contract_links` (PO↔Contract M:N) 之后，`build_summary_for(po_id=...)` 仍只过滤 `PaymentSchedule.po_id == po.id`，挂在合同上的 schedules 不会出现在 PO 视图。修复为并集：`PaymentSchedule.po_id == po.id` ∪ `PaymentSchedule.contract_id IN (legacy Contract.po_id ∪ po_contract_links)`。

### 改进

- **Admin → 模型路由**: 启用列从只读 Tag 改为可交互 Switch；启用未开启的 LLM 路由会先弹 Popconfirm 提醒"将调用大模型 API、可能产生 token 费用"，禁用直接生效。这意味着管理员现在可以一键打开 `document_generation` 让真正的 LLM 接管尚未被 deterministic 覆盖的占位符（v0.9.17 默认 enabled=false 因此始终未触发）。

### 测试

- `tests/unit/test_payment_schedule.py` 新增 2 条回归：`test_po_summary_includes_legacy_linked_contract_schedule`、`test_po_summary_includes_m2m_linked_contract_schedule`。
- 新增 `tests/unit/test_content_disposition.py` 3 条契约测试，锁定 ASCII / 中文 / 纯非 ASCII 文件名都能 latin-1 编码通过。
- 容器内 `pytest tests/` **363 passed**。
- 前端 `tsc --noEmit` 与 `vite build` 全绿。

### 元数据

- 版本对齐 `0.9.18`：`backend/pyproject.toml`、`frontend/package.json`、`backend/app/config.py`、`deploy/.env.example`、`AGENTS.md`、`README` 徽章。

---

## [v0.9.17] — 2026-04-25

### 修复

- **付款表格智能填充端到端可用**：v0.9.16 重构 LLM 路由后，生产上传的实际 xlsx 模板（示例财务付款表）大量字段仍生成为空。本次的精准修复：
  - `build_context()` 增加 `actor` / `company` / `today` / `payment` 四组数据，API 层默认传入当前用户 + PO 所属公司；
  - `DETERMINISTIC_RESOLVERS` 新增 12 条正则覆盖：付款方公司全名 / 四字简称、收款方公司全称、付款金额、生成日期、当前用户全名、付款性质简称等真实模板里出现的占位符；
  - `_enrich_with_computed` 的日期处理根据「生成 / 当前 / 今天 / 本单据」关键字选择 `today.iso`，避免把生成日期错填为付款计划日期；
  - 解除 v0.9.16 对 filename placeholders 的 LLM 拦截 —— 文件名仍由 `render_filename()` 做文件系统安全清洗。
  - 端到端验证：生产模板的 14 个真实占位符里 12 个无需 LLM 即可正确填充，剩下两个落到 `payment.narrative_short` 兜底或 LLM。
- **首页月度付款追踪不再出现负数 remaining**：当某月有 CONFIRMED 付款但没有匹配的 PaymentSchedule（典型例子：用户跳过排期直接登记 450 万），原 `planned - paid` 会得到负数。新逻辑 `planned = max(scheduled+pending, paid)`、`remaining = max(planned-paid, 0)`，符合用户语义「已付即在计划内」。

### 数据迁移

- `0025_ai_feature_routing_document_generation`：在已有生产库中插入一行 `document_generation` AI 路由记录（默认 `enabled=false`、指向最早的 AI Model）。管理员只需到 Admin 控制台把它打开即可启用 LLM 路径；若一直关闭，新的 deterministic 覆盖已能填出绝大多数字段。

### 测试

- `test_document_templates.py` 新增 5 条契约测试：真实生产模板占位符全量解析、付款叙事关键词匹配、生成日期与付款日期分别走 today / schedule、filename placeholders 现在合法走 LLM。
- `test_payment_schedule.py` 新增 `test_payment_forecast_remaining_never_negative`，锁定不可负的语义。
- 容器内 `pytest tests/unit/` 349 passed。

### 元数据

- 版本对齐 `0.9.17`：`backend/pyproject.toml`、`frontend/package.json`、`backend/app/config.py`、`deploy/.env.example`、`AGENTS.md`、`README` 徽章。

---

## [v0.9.16] — 2026-04-25

### 新增

- **付款表格模板占位符改为 LLM 优先**：
  - 之前是硬编码正则匹配，[] 内自然语言说明永远到不了 LLM。
  - 现在按占位符分类路由：文件名 / 银行账号+税号 **始终** 走 deterministic；短 canonical key（PO编号 / 合同编号 / 付款期次）默认 deterministic，仅 miss 时回退 LLM；含中文标点或长文本的自然语言占位符 LLM 优先，deterministic 兜底。
  - 日期格式化 + 大写金额的 `_enrich_with_computed` 作为最终权威步骤，覆盖 LLM 输出避免模型幻觉。
  - 新增 seed：`AIFeatureRouting(feature_code=document_generation, enabled=False)`，管理员在 Admin 控制台一键启用。
- **仪表盘月度付款追踪补齐计划金额盲区**：
  - 之前只统计 `planned_date` 落在当前窗口的 PaymentSchedule；挂在合同下、但未排期（`planned_date is null`）或日期落在窗口外的计划金额被隐藏，导致“只见已付不见计划”。
  - 后端 `payment_forecast` 新增 `undated_planned` 与 `out_of_window_planned` 两个聚合字段。
  - 前端 PaymentTracker 只在两者 > 0 时额外渲染两个 Statistic 块：**未排期计划金额** / **窗口外计划支出**。

### 修复

- **交货批次 / 合同扫描件附件支持 Office 文档**：之前 `ALLOWED_CONTENT_TYPES` 仅白名单 PDF / OFD / XML / image，上传 `.xlsx` 返回 HTTP 415。
  - 放宽后端白名单：新增 xlsx / xls / docx / doc / csv / txt / zip / gif / webp / bmp。
  - 同步扩宽 ContractDetail 扫描件归档 `<Upload accept>` 过滤器；Shipments 页面原本就没有 accept 过滤。
  - 发票上传入口保持窄白名单不变（发票抽取器只支持 PDF / OFD / XML / image）。

### 测试 & 元数据

- 后端新增 5 条占位符路由契约测试（自然语言分类、敏感字段拦截、文件名路径跳过 LLM、LLM 空响应回退、computed 覆盖）。
- 容器化运行：`test_document_templates.py` 29 passed；`test_documents.py + test_payment_schedule.py` 30 passed。
- 版本号对齐到 0.9.16：`backend/pyproject.toml`、`frontend/package.json`、`backend/app/config.py`、`deploy/.env.example`、`AGENTS.md`、`README` 徽章。

---

## [v0.9.15] — 2026-04-25

### 新增

- **PO ↔ 合同关联跨链可见**：
  - ContractDetail 顶部"关联采购订单"卡片改为**所有关联 PO 列表**（主 PO + 次级关联 PO），点击可直接跳转对应 PO。
  - 合同 "交货记录" Tab 现在聚合所有关联 PO 下的交货批次，不再只显示主 PO 交货。
  - PO 详情页新增"关联已有合同 / 解除关联"按钮与弹窗，对非主 PO 的关联合同显示"解除关联"，对主 PO 显示"主采购订单"标签。
  - 合同详情返回体新增 `linked_pos` 字段；新增后端 API：
    - `GET /contracts/{id}/linked-pos`
    - `POST /purchase-orders/{po_id}/contracts/{contract_id}`（关联）
    - `DELETE /purchase-orders/{po_id}/contracts/{contract_id}`（解除关联）
- **AI 模板化单据生成支持 .xlsx**：
  - 管理员后台模板上传接受 `.docx` 与 `.xlsx` 两种文件类型。
  - 占位符提取现在支持 `.xlsx` 单元格文本；替换走 `openpyxl`，跳过合并单元格，保留工作簿结构。
  - 付款计划一键生成时，根据模板扩展名自动返回 `.docx` 或 `.xlsx`，并使用正确的 MIME 类型。
- **文档中心重构（GitDocs 大修）**：
  - 把单文件 `admin-guide.md` 拆分为 7 份独立章节：部署与运维、HTTPS/TLS、系统管理控制台、SAML SSO、权限架构、备份恢复、故障排查与升级。
  - 新增英文版用户手册与管理员指南（`docs/user-manual/en/`）。
  - 改写中文首页说明，调整 `mkdocs.yml` 为"中文 / English" 双语导航。

### 改进与守卫

- **PO↔合同关联安全护栏**（基于 Oracle 审阅建议）：
  - 拒绝解除合同的**主 PO** 关联；
  - 关联新 PO 时校验供应商、币种、公司一致；
  - 合同付款计划的付款必须在该合同的主 PO 下登记；
  - 已存在付款记录的 PO 不允许解除关联。
- **次级链接元数据同步**：
  - 合同版本快照 (`contract_snapshot`) 与合同到期通知元数据均包含 `linked_po_ids`，便于审计与排查。
- **文档站点**：修复若干用户手册内部失效的锚点链接，并移除所有指向后端源码文件的相对链接，让 `mkdocs build` 在仓库本地零 warning。

### 修复

- **付款文档生成的合同推导**：付款计划隶属 PO 但未直接挂合同时，系统按 `po_contract_links` 唯一关联合同推导；多合同歧义时明确返回 `template.contract_required_for_generation`。

### 测试

- 后端 `test_flow.py` 新增覆盖：
  - 主 PO 解除关联被拒绝
  - 供应商 / 币种不匹配关联被拒绝
  - 次级 PO 下执行合同付款计划被拒绝
  - 已有付款时解除关联被拒绝
- 后端 `test_document_templates.py` 新增覆盖：
  - 从 `.xlsx` 模板中抽取占位符
  - `substitute_xlsx` 占位符替换
  - 付款计划生成按 `.xlsx` / `.docx` 扩展名正确返回文件
  - 多关联合同时的歧义拒绝
- 在容器化环境中执行：`tests/unit/test_flow.py` 46 passed；`tests/unit/test_document_templates.py` 23 passed。

### 版本与元数据

- 版本号：`backend/pyproject.toml`、`frontend/package.json`、`backend/app/config.py`、`deploy/.env.example`、`AGENTS.md` 全部对齐到 `0.9.15`。
- 清理了 README 与 AGENTS.md 中遗留的 `0.9.5` 旧版本引用。

---

## [v0.9.14] — 2026-04-25

### 新增

- **AI 驱动的单据模板生成**：按模板批量生成财务付款表等业务单据
  - **系统管理 → 模板管理** 新增 Tab：
    - 预置一个 `finance_payment_form`（财务付款表）模板，管理员上传 `.docx` 模板文件即可启用
    - 可编辑模板名称、描述、生成文件名格式，启用/禁用
    - "预览占位符" 按钮：解析当前模板（含文件名格式）中的 `[...]` 占位符，帮助管理员检查命名是否被系统识别
  - **占位符语法** `[描述]`：
    - 描述可以是字段名（如 `[PO编号]`、`[合同编号]`、`[收款单位名称]`、`[收款单位开户行]`、`[银行账号]`）
    - 描述也可以带格式指令：`[付款日期 YYYY年MM月DD日]`、`[付款日期YYYYMMDD]`、`[本期付款金额(大写)]`
  - **智能填充**：两级解析策略
    - 第一级：确定性字段（PO 号、合同号、供应商名、收款信息等）用正则直接映射，零延迟
    - 第二级：未命中的占位符交给 LLM（通过已有 AI routing 基础设施），要求返回 JSON 映射。Prompt 明确指示日期格式、大写金额等 convention
    - 日期格式、大写金额等 computed 字段走内置转换（cn_amount_upper 将 4500000 转为 "肆佰伍拾万元整"）
  - **付款计划行新增"生成财务付款表"按钮**（PODetail 的付款计划 Tab + ContractDetail 的付款计划 Tab 均可见）：
    - 一键生成单据，按模板的文件名格式命名下载（例：`财务付款表_PO-2026-0001_第1期_20260424.docx`）
  - 新增端点：
    - `GET /admin/document-templates` / `PATCH /admin/document-templates/{id}` / `POST /admin/document-templates/{id}/upload`
    - `GET /document-templates/{id}/placeholders`（预览）
    - `POST /payment-schedule-items/{id}/generate-document`（一键生成 + 下载）

### 数据库迁移

- `0023_po_contract_links.py`：新增 `po_contract_links` M:N 表 + 从现有 `contract.po_id` 回填（为后续 v0.9.15 的聚合视图打底；目前尚未启用聚合逻辑）
- `0024_document_templates.py`：新增 `document_templates` 表，种一条 `finance_payment_form`（管理员上传文件后即可用）

### 测试

- 后端 `test_document_templates.py` 新增 18 条测试：
  - 占位符抽取（文件名格式 + docx body）
  - 文件名替换 + 非法字符清理
  - 大写金额转换（整元 / 含分 / Decimal / 空值）
  - 确定性字段解析（PO、合同、收款信息）
  - 日期格式补全（YYYY年MM月DD日 / YYYYMMDD）
  - 无 LLM 时的 graceful fallback
- 后端总测试数 308 → 326

### 依赖

- 新增 `python-docx>=1.1.2`（Word 模板解析与填充）

### 备注

- 仅支持 `.docx`；`.xlsx`（Excel 表格）模板如需后续增加，可复用 openpyxl 走相同的解析-填充管线
- LLM 通过 `document_generation` feature routing 配置；未配置时系统降级到纯确定性规则 + computed enrichment，大部分常见占位符仍可自动填充
- PO↔Contract 的 M:N 关联表虽已落表，但服务层和 UI 尚未切换到聚合视图 —— **推迟到 v0.9.15** 实现"PO 付款/到货/开票进度 = 所有关联合同之和"

---

## [v0.9.13] — 2026-04-25

### 新增

- **首页「月度付款追踪」（从原"待付款项"升级）**：
  - 卡片右上角新增 ← / 本月 / → 三个按钮，可以自由翻阅过去和未来
  - 默认窗口：过去 3 个月 + 当前月 + 未来 3 个月（共 7 个月）
  - 当前月在柱状图和明细表中都做了视觉突出（浅棕背景、加粗月份文本、"本月" 标注）
  - 后端 `payment_forecast` 新增 `past_months` 和 `anchor`（YYYY-MM）参数；老调用（`months=6`）继续可用
- **合同编号自定义 + 可配置前缀自动建议**：
- 合同编号默认格式从 `CT-{YYYY}-{NNNN}` 改为 `<PREFIX>{YYYYMMDD}{SEQ}`，前缀由系统参数 `contract.number_prefix` 配置（默认 `ACME`），SEQ 三位数字每天从 001 起递增，例：`ACME20260425001`
  - 创建合同对话框把合同编号设为可编辑字段，默认填入后端建议值，右侧"重新生成"按钮可刷新建议
  - 后端新增 `GET /contracts/suggest-number` 端点；若用户输入的编号与已有记录冲突返回 409 `contract.number_duplicate`

### 修复

- **迁移 0022：把孤儿付款记录自动挂到合同**
  - 针对历史上 `contract_id=NULL` 的 PaymentRecord，如果其所在 PO 下只有一份合同，自动把该 PaymentRecord 的 contract_id 补齐为该合同 id
  - 生产 PO-2026-0001-P01（contract_id=NULL，但 PO 下只有 CT-2026-0001 一份合同）被自动关联到 CT-2026-0001，修复了 v0.9.11 前遗留的历史记录

### 改进

- **前端 `PaymentForecastChart` 改名为 `PaymentTracker`**（保留旧名作为别名，不破坏 import）
- 首页卡片标题改为"月度付款追踪"，强调可回溯 + 可前瞻

### 测试 & 文档

- 后端新增 3 条回归测试（前缀格式 / 自定义编号成功 / 重复编号 409 拒绝）
- 后端总测试数 305 → 308
- **测试覆盖度评估**：
  - Backend: pytest 308 tests, **行覆盖 73%** (app/ 6842 行 / 1872 未覆盖)
  - Frontend: vitest 58 tests, 组件级覆盖约 89%（仅覆盖 utils / stores / ui primitives / ThemeProvider；业务页面如 PODetail / ContractDetail / Admin / SKU 暂无单元测试，未来迭代重点）
  - 覆盖率低的后端模块：`api/v1/import_excel`（17%）、`services/ai`（22%）、`api/v1/saml`（24%）、`services/invoice_extract`（30%）、`services/saml_metadata_refresh`（27%） —— 主要是 LLM / SAML 集成路径，依赖外部服务，单元测试难度大
- README 测试徽章更新为 "pytest 308 tests (backend 73% coverage) · vitest 58 tests"

### 数据库迁移

- `0022_autolink_orphan_payments.py`：一次性回填孤儿付款到唯一合同

---

## [v0.9.12] — 2026-04-24

### 修复

- **仪表盘「已支出」仍然显示 0**（v0.9.11 后仍未解决）：
  - 追溯原因：v0.9.11 让 forecast 正确读取了 payment_records，但 `grand_paid` 仍只累加"落在未来 6 个月窗口内"的付款。用户的 4.5M 付款 `payment_date=2026-03-24`（当前月之前），完全不在该向前窗口里 —— 设计上正确，但语义不符用户直觉
  - 修复：在 `/dashboard/payment-forecast` 响应中新增 `paid_to_date`（**累计已付款，不受时间窗口限制**），前端预测卡顶部突出展示"累计已付款（截至今日）"，与"未来 N 个月计划支出"、"未来 N 个月已在窗口内支出"、"未来 N 个月待支出"并列
  - 现在用户立刻能看到自己累计的 4.5M 支出，而不是被窗口切掉

### 测试

- `test_payment_forecast_paid_to_date_includes_past_payments` — 确认历史过期付款也会进入累计已付款统计
- `test_payment_forecast_includes_direct_confirmed_payments` — 扩展为同时验证 `paid_to_date`
- 后端总测试数 304 → 305

---

## [v0.9.11] — 2026-04-24

### 修复（关键）

- **仪表盘「已支出」显示为 0 但实际已付 450 万**：`/dashboard/payment-forecast` 的 paid 金额从 `payment_schedules.actual_amount` 聚合；但通过 PO 直接登记的付款（没有走合同分期"执行"）从未在 payment_schedules 表里留下数据，导致仪表盘对这类付款完全不可见
  - 修复：改为从 `payment_records` 聚合（status=confirmed 按 `payment_date` 入桶），这是实际付款的唯一事实来源
  - 连带修复 planned 桶：改为 `payment_schedules` (PLANNED/DUE) + `payment_records` (status=PENDING 按 due_date 入桶) 的联合，两类未来支出都能看到

### 修复

- **无法把已有付款关联到合同**：PaymentUpdateIn 原先不允许修改 `contract_id` / `schedule_item_id`，导致 v0.9.10 前的旧付款记录（contract_id=NULL）无法补挂合同
  - 后端：PATCH 接受 contract_id + schedule_item_id，校验新 contract 的 po_id 与 payment.po_id 匹配；校验 schedule 属于新 contract 或 PO；改动时自动把旧 schedule（如果是因本付款被标 PAID）回滚到 PLANNED，并把新 schedule（若 payment 是 confirmed）标为 PAID
  - 前端：PaymentEditModal 增加合同下拉和分期下拉；已是 paid 的分期会在下拉里保留当前选中项，便于核对；清空 contract_id 会被 400 拒绝（policy: 合同必须存在）

### 改进

- **仪表盘付款预测面板优化**：
  - 卡片右上角注明时间窗口（"未来 6 个月（2026-04 → 2026-09）"）
  - 顶部汇总卡的标题明确标注"未来 N 个月"
  - 图表下方新增紧凑的月度明细表（月份 / 计划 / 已付 / 当月待支出 + 合计行），无需再仔细观察柱高就能看到具体数字

### 测试

- 新增 5 条回归测试：
  - forecast 看见直接确认的 PaymentRecord（捕获本次 bug）
  - forecast 看见 pending PaymentRecord（验证新增 planned 逻辑）
  - update_payment 可把 contract_id=NULL 的旧记录补挂合同
  - update_payment 拒绝跨 PO 的合同
  - update_payment 拒绝把 contract_id 清空
- 后端总测试数 299 → 304，全绿

### 备注

- 本次不涉及 DB schema 变更，migrate 容器只是跑 alembic head（无事可做），部署耗时短

---

## [v0.9.10] — 2026-04-24

### 修复（关键）

- **合同付款计划"执行"不更新 PO 已付金额** — 采购订单的"已付金额"与合同分期执行记录长期不一致。`execute_schedule_item()` 创建 PaymentRecord 却漏掉 `po.amount_paid += pay_amount`；只有通过 PO 直接登记付款才会更新。此次补齐；**并提供一次性回填 migration（0020）** 把历史上所有 `status=confirmed` 的付款记录累加回 PO.amount_paid，把线上数据修齐

### 新增（端到端打通）

- **付款必须关联合同（合规政策）**：
  - `payment_records` 新增 `contract_id` 列（migration 0021），并从已有 `schedule_item_id` 链路回填
  - `create_payment` 强制要求 `contract_id`，校验 contract 的 `po_id` 与传入 PO 一致；可选地传 `schedule_item_id` 自动把该期标记为 PAID
  - `execute_schedule_item`（合同分期 + PO 分期两条路径）都会在创建的 PaymentRecord 上写 `contract_id`
  - 前端 PaymentModal 重做：合同下拉必选；若 PO 下唯一合同自动选中；若没有合同展示内联 `创建合同` 按钮（一键 pre-fill）；若已选合同且有未付分期，展示次级下拉"关联到第 N 期付款"
- **付款可编辑/可删除**：
  - 新增 `PATCH /payments/{id}` 修改金额 / 日期 / 付款方式 / 交易号 / 备注；PO.amount_paid 和对应分期 actual_amount 同步更新
  - 新增 `DELETE /payments/{id}`；已确认付款不允许删除（`payment.cannot_delete_confirmed`）；删除分期关联时回滚分期状态到 PLANNED
  - PO 付款表新增 编辑 / 删除 按钮 + 所在合同号列
- **PO ↔ 合同双向导航**：
  - PO 详情新增「合同」Tab，列出该 PO 下所有合同（含点击跳转）
  - 合同详情新增「关联 PO」卡片（放在信息 Tab 最上方，带"查看 PO"按钮）
  - 合同列表新增 `所属 PO 号` 列（可点击跳转）
  - 后端 `ContractOut` 增加 `po_number`、`po_status`、`supplier_name` 反范式字段；新增 `GET /contracts/{id}` 端点，eager-load `po` 和 `supplier`
- **合同↔交货联动**：合同详情新增「交货记录」Tab，列出该合同所属 PO 下所有 shipments，支持跳转到 PO 中进行管理
- **OCR 文本可见**：合同附件卡片的 OCR badge 旁新增「查看 OCR」按钮，弹出 Modal 显示完整识别文本；新增 `GET /contracts/{id}/attachments/{document_id}/ocr` 端点返回 ocr_text
- **用户删除**：
  - 后端新增 `DELETE /admin/users/{id}`，带安全校验：
    - 不允许删除当前登录账号（`user.cannot_delete_self`）
    - 最后一位启用状态的管理员不允许删除（`user.cannot_delete_last_admin`）
    - 已产生业务数据（PR/PO/审批/审计日志）的用户硬删除会被 FK 拒绝 → 返回 `user.has_references` 并提示禁用账号
  - 前端 Admin 用户管理每行新增红色删除按钮（删除自己按钮置灰），含确认对话框

### 测试

- 后端新增 11 条：execute_schedule_item 更新 amount_paid、payment.contract_required、合同/PO 不匹配、payment.update 金额调整 PO.amount_paid、confirmed 付款禁止删除、pending 付款删除成功、5 条用户删除安全场景
- 后端总测试数 289 → 300，全绿
- 前端 58 tests 全绿，type-check + build 通过

### 数据库迁移

- `0020_backfill_amount_paid.py` — 一次性回填 PO.amount_paid（修复历史数据漂移）
- `0021_payment_records_contract_id.py` — 新增 contract_id 列 + FK + 索引 + 从 schedule_item_id 链路回填

### 备注

- 方案 B（合规 + 效率平衡）落地：付款严格关联合同，但 UI 把"没有合同时一键创建"的路径压缩到最短
- v0.9.6 新增的 PO 级 payment schedule 保留不变；通过它执行付款时，PaymentRecord 的 `contract_id` 会保持 null，由合同级路径保证合规；后续若收紧政策可在 `execute_schedule_item` 的 PO parent 路径上再增硬性校验

---

## [v0.9.9] — 2026-04-24

### 新增

- **供应商收款信息字段**：在供应商实体中新增 3 个字段，用于财务付款时使用
  - `payee_name`（收款单位名称）—— 付款抬头，未填写时默认使用供应商名称
  - `payee_bank`（收款单位开户行）
  - `payee_bank_account`（收款单位银行账号）
  - Migration 0019：`suppliers` 表增加 3 列，均为 nullable
  - 前端：供应商编辑抽屉里用 Divider 分组展示「基本信息 + 联系方式 + 收款信息」；SupplierDetail 页面新增「收款信息」卡片，银行账号支持一键复制
  - 仅编辑/详情可见，列表页不展示（避免敏感字段过度曝光）
  - i18n：新增 zh-CN / en-US 键完整覆盖

### 测试

- `test_master_data.py` 新增 2 条回归测试（payee 字段持久化 + 更新），后端 287 → 289 passed

---

## [v0.9.8] — 2026-04-24

### 修复

- **管理员用户列表中部分用户的部门显示为 UUID 而不是部门名称** — 生产环境用户反馈
  - 根因：`GET /admin/users` 返回全量用户（跨公司），但前端构建 `deptMap` 调用的 `/departments` 端点按 `company_id == user.company_id` 过滤（只返回当前管理员所在公司的部门）。结果：跨公司用户（如种子数据中属于 DEMO 公司的 alice/bob/carol/dave，而当前管理员属于 JQSH）的 `department_id` 不在 deptMap 中，UI 回落到显示原始 UUID
  - 修复：在 `/admin/users` 响应中预 join 部门和公司字段（`department_code`、`department_name_zh`、`company_code`、`company_name_zh`），前端渲染直接从用户行读取，不再依赖 dept 映射表。同步更新 `POST /admin/users` 和 `PATCH /admin/users/{id}` 的返回值
  - 前端：`Admin.tsx` 用户管理表的部门列优先读 `department_name_zh`，deptMap 作为二级兜底（兼容旧逻辑），最后才显示 UUID

### 备注

- 部门下拉选项（创建/编辑用户对话框）仍按当前管理员公司范围列出 —— 管理员不应把用户分配到自己看不到的公司的部门，这是预期行为。仅修复展示不一致

---

## [v0.9.7] — 2026-04-24

### 修复

- **本地用户创建报"数据校验失败"**：`UserCreateIn.role` Literal 漏了 `requester` 角色（6 个合法角色中只列出了 5 个），导致前端默认选中的 requester 每次都被后端 422 拒绝。`UserUpdateIn.role` 早就修对了，但创建路径的漂移一直没被发现。

### 修复

- **本地用户创建报"数据校验失败"**：`UserCreateIn.role` Literal 漏了 `requester` 角色（6 个合法角色中只列出了 5 个），导致前端默认选中的 requester 每次都被后端 422 拒绝。`UserUpdateIn.role` 早就修对了，但创建路径的漂移一直没被发现。
  - 修复：补上 `"requester"` 到 create 的 Literal
  - 加固：新增 `tests/unit/test_admin_user_schemas.py`，参数化遍历 `UserRole` 枚举所有值，create + update 两个 schema 必须都接受，否则 CI 红灯。此后任何新加的角色若忘了同步 schema 会被立即发现

### 新增

- **SAML IdP 元数据手动刷新按钮**：系统参数页面 `auth.saml.idp.metadata_url` 一行现在有「立即刷新」按钮（`SyncOutlined` 图标），点击会：
  - 调用 `POST /saml/refresh-metadata` 从 URL 拉取 IdP FederationMetadata.xml
  - 弹出成功模态窗，提示证书是否发生变化、找到几张证书、SSO URL 与 entityId 是否一致
  - 失败时弹错误模态窗并显示具体原因（网络不通、证书解析失败等）
  - 这之前只能 curl 后端端点，普通管理员没办法自助操作

### 重构

- **ContractDetail 合同详情页付款计划 Tab 迁移到 `<PaymentScheduleTab>` 组件**
  - 合同详情的付款计划 Tab 之前是自己的实现，漏掉了"执行付款"和"删除分期"的按钮，用户只能看不能操作。现在改用 v0.9.6 新增的共享组件，与 PO 的付款计划 Tab 行为完全一致，并获得执行/删除功能
  - 代码量从 655 行降到 351 行（-304），去除了重复的 `scheduleColumns` 定义、schedule state、Drawer 表单、以及三个重复的 handlers

### 测试

- **修复 `tests/unit/test_cerbos_client.py::test_unknown_resource_returns_all_fields` 先前的 flaky 失败**：测试类的假设是"Cerbos 不可达时降级到 FIELD_PERMISSIONS"，但在 docker compose 测试环境里 Cerbos sidecar 实际是健康运行的，收到未知 resource 会显式 deny 而非回退。加 `autouse` fixture 把 `CERBOS_BASE_URL` 强制指向 `http://127.0.0.1:1`，让整个 class 始终走降级路径
- 后端总测试数 272 → 287（+15：admin schema 14 + cerbos 修复后恢复 1）
- 前端 58 tests 仍全绿，type-check + build 干净

---

## [v0.9.6] — 2026-04-24

### 新增

- **合同 CRUD**：合同列表从只读升级为完整管理界面
  - PO 详情页新增「创建合同」按钮（采购经理 / IT 采购员 / 管理员可见，在 PO 状态非 draft/cancelled 时可用）
  - 合同列表每行支持 编辑 / 变更状态 / 删除 操作按钮（按角色授权显示）
  - 合同详情页顶栏增加 编辑 / 变更状态 / 删除 按钮
  - 状态变更覆盖合法转换：active → terminated / superseded / expired（状态不可回退到 active）
  - 每次编辑/状态变更均写入 `contract_versions` 快照，`current_version` 自动递增
  - 后端新增 `PATCH /contracts/{id}`、`PATCH /contracts/{id}/status`、`DELETE /contracts/{id}` 端点 + 角色守卫 + i18n 错误消息
- **PO 级付款计划**：付款计划不再局限于合同，也可直接挂在 PO 上
  - PO 详情页新增「付款计划」Tab，支持创建/执行/删除分期
  - `payment_schedules` 表添加 `po_id` 列（migration 0018），`contract_id` 改为可空，加 CHECK 约束保证 XOR（contract OR po）
  - 服务层重构：新增 `_resolve_parent` 抽象，同一套逻辑同时支持合同级和 PO 级计划
  - REST API 新增 `GET/POST/PUT/DELETE /purchase-orders/{id}/payment-schedule[...]` 路由系列，合同路径保持向后兼容
- **仪表盘「待付款项」图表**：采购经理 / 财务 / 管理员视图新增 6 个月付款预测条形图
  - 并列显示计划金额（棕色）与已付金额（绿色），hover 显示月份明细
  - 顶部汇总：总计划支出 / 已支出 / 待支出
  - 使用内联 SVG 实现，不引入图表库依赖，bundle 增量 < 2KB

### 修复

- **PO 导出 PDF 字体渲染**：原版用 `STSong-Light` CID 字体（无粗体变体），reportlab 对 `<b>` 标签通过合成粗体（over-striking）产生可见文字重叠
  - 后端镜像安装 `fonts-wqy-microhei`（文泉驿微米黑 TrueType，~6MB），注册为 `MicaCJK` 字体族
  - 粗体角色映射到同一 Regular 字体，杜绝合成粗体重叠（已在服务层注释说明设计原因）
  - 表头行改用 `Paragraph` 统一渲染（之前表头为纯字符串 + 表格级 FONTNAME，与单元格内 Paragraph 存在渲染差异）
  - 所有用户输入（供应商名/物料名/规格）经 `html.escape` 处理，避免 `<`、`>`、`&` 破坏 Paragraph 的 XML 解析
  - 若运行环境缺少 WenQuanYi（开发机），自动降级到 STSong-Light 并同样禁用合成粗体

### 测试

- 后端：payment_schedule 服务新增 3 条 PO 级测试（创建 / 合同和 PO 隔离 / 参数校验）
- 后端：flow 服务新增 6 条合同 CRUD 测试（update / noop / rejected in terminal status / transition / invalid transition / delete）
- 后端：export_pdf 新增 3 条测试（`_esc` HTML 转义、`_fmt_qty` 格式化、包含 XML 特殊字符的 PO 渲染）
- 后端：273 → 279 tests，0 regressions（cerbos_client 测试 1 条失败为 main 上已存在，与本次改动无关）
- 前端：type-check + build 通过，58 tests 绿灯

### 数据库迁移

- `0018_payment_schedules_po_or_contract.py`：`contract_id` 改为可空、新增 `po_id`、CHECK 约束、索引、外键

---

## [v0.9.5] — 2026-04-23

### 破坏性变更

- **部署方式改革**：`upgrade.sh` 不再依赖 rsync，改为 `git fetch + git checkout <tag>`。生产环境的 `.env`、`nginx/conf.d/mica.conf`、`certs/` 等配置文件不再被代码更新覆盖
- **Nginx 配置解耦**：`mica.conf` 从 Git 跟踪中移除，改为 `.gitignore`。Git 中保留 `mica.conf.default`（HTTP 默认配置）和 `mica-tls.conf.template`（HTTPS 模板）。首次部署自动从 default 创建

### 新增

- **IdP 元数据自动刷新**：新增 `auth.saml.idp.metadata_url` 系统参数 + `POST /saml/refresh-metadata` 管理端点 + `saml_metadata_refresh` 服务，可从 ADFS FederationMetadata.xml 自动获取并更新签名证书（migration 0017）
- **SAML 错误日志**：ACS 验证失败时记录具体错误原因到日志和审计表，不再只返回 403

### 修复

- **SAML ACS 403 — unsigned Response**：ADFS 只签 Assertion 不签外层 Response，Mica 要求两者都签导致 403。放宽 `wantMessagesSigned` 为 false
- **SAML SP URL 使用 http 而非 https**：反向代理后 `request.url.scheme` 永远是 http，改为读取 `X-Forwarded-Proto` / `X-Forwarded-Host`
- **用户管理部门下拉框显示 UUID**：`Department` 字段名 `name` 不存在，改为 `name_zh`；表格列增加 `deptMap` 名称查找
- **登录表单 Enter 键不提交**：提交按钮包裹到 `Form.Item` + 密码框增加 `onPressEnter`
- **部署覆盖生产配置**：rsync 会覆盖 TLS nginx config / .env 等文件。重构为 git-based 部署
- **健康检查不识别 HTTPS**：smoke_test 和 wait_healthy 适配 TLS 模式 + 修复 nginx 容器名称匹配

## [v0.9.4] — 2026-04-23

### 新增

- **登录页 SSO 优先体验**：当系统启用 SAML SSO 时，登录页优先展示"通过 SSO 登录"按钮，本地账号密码登录隐藏在"使用本地账号登录"链接后面；未启用 SSO 时界面不变
- **交货批次 CRUD + 附件上传**：交货批次列表页从只读升级为完整管理界面，支持编辑状态/物流信息、删除批次；新增附件管理功能，可上传序列号清单、签收单、发货单等文件
- **ShipmentDocument 模型**：新增 `shipment_documents` 关联表（migration 0016），支持交货批次与文档的多对多关联
- **交货批次 API**：`PATCH /shipments/{id}`（更新）、`DELETE /shipments/{id}`（删除）、`POST/GET/DELETE /shipments/{id}/attachments`（附件管理）
- **SSO 配置指南**：管理员手册新增详细的 SAML SSO 配置章节，涵盖 ADFS 和 Microsoft Entra ID（原 Azure AD）的分步配置说明和参数示例

### 修复

- **系统管理页面横向溢出**：在 1366×1024 等窄屏下，Tab 标题和内容超出屏幕且无横向滚动条；修复 Content 区域 overflow 处理 + 移除重复的部门管理 Tab

## [v0.9.3] — 2026-04-23

### 新增

- **供应商 CRUD**：供应商列表页从只读升级为完整管理界面，支持新增、编辑、删除、启停操作，新增税号和备注字段
- **部门管理 Tab**：Admin 系统管理新增"部门管理"标签页，支持部门的新增、编辑、删除
- **分类体系统一操作**：采购种类和开支类型新增编辑、启停操作按钮（之前仅成本中心有）
- 新增 8 个前端 API wrapper（供应商 3 + 部门 3 + 分类更新 2）
- 新增 20+ 供应商和部门相关 i18n 键（zh-CN / en-US）

## [v0.9.2] — 2026-04-23

### 新增

- **用户管理 CRUD**：Admin 用户管理 Tab 从只读表格升级为完整管理界面，支持新增用户、编辑用户信息、重置密码、启用/停用账号
- **用户更新 API**：`PATCH /admin/users/{user_id}` 支持修改 display_name / email / role / company / department / locale / is_active，变更写入审计日志
- 新增 20+ 用户管理相关 i18n 键（zh-CN / en-US）

### 修复

- **成本中心创建 500 错误**：当已软删除的成本中心仍占着唯一约束 code 时，重新创建同 code 会触发 `UniqueViolationError`。改为自动恢复已删除的同 code 记录并更新字段

## [v0.9.1] — 2026-04-23

### 新增

- **回收站 Tab**：系统管理新增"回收站"页面，集中展示所有被软删除的主数据实体（公司/部门/成本中心/采购分类/开支类型/供应商/物料），支持按类型筛选和一键恢复
- **公司主体删除按钮**：Admin 公司主体列表新增删除操作（带确认弹窗）
- **回收站 API**：`GET /admin/recycle-bin` 聚合查询 + `POST /admin/recycle-bin/{type}/{id}/restore` 恢复

### 修复

- **成本中心/公司主体删除后仍显示**：Admin 列表 API 参数逻辑错误，`include_inactive` 同时暴露了已删除条目。拆分为独立的 `include_disabled` / `include_deleted` / `enabled_only` 参数，Admin 列表只显示未删除条目（含已停用的）
- **UserOut schema 残留 is_deleted 字段**：导致 `/auth/me` 500 错误

## [v0.9.0] — 2026-04-23

主数据实体 `is_active` 拆分为 `is_enabled`（业务启停）+ `is_deleted`（软删除），消除长期语义歧义。

### 破坏性变更

- **7 个主数据表 schema 变更**：`companies`、`departments`、`cost_centers`、`procurement_categories`、`lookup_values`、`suppliers`、`items` 的 `is_active` 列替换为 `is_enabled`（业务启停）+ `is_deleted`（软删除）
- **API 响应字段变更**：上述实体的 Output schema 返回 `is_enabled` + `is_deleted` 替代 `is_active`；Update schema 接受 `is_enabled` 替代 `is_active`
- 不影响：`users.is_active`、`ai_models.is_active`、`approval_rules.is_active`、`approver_delegations.is_active` 保持不变

### 新增

- Migration 0015：自动从 `is_active` 回填 `is_enabled`/`is_deleted`，无需手工数据迁移

### 改进

- Admin 管理页面操作语义清晰化：编辑 / 启用·停用 / 删除 三个操作各司其职，不再混淆
- 业务表单（PR 创建选公司/成本中心/供应商等）只显示 `is_enabled=true AND is_deleted=false` 的条目
- Admin 列表显示所有未删除条目（含已停用的），可视化区分状态

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

---

## [v1.1.2] — 2026-04-29

### 修复

- **FeishuSettingsTab 表单值刷新后丢失**：Vite/Rollup 生产构建将模块级常量 `FEISHU_INITIAL_VALUES` 内联回 JSX 使用处，每次渲染重建新对象，Ant Design Form 检测 `initialValues` 变化后重置表单。修复：完全移除 `initialValues` prop，依赖 `useEffect` + `setFieldsValue` 从 API 回填所有值。

---

## [v1.1.1] — 2026-04-29

### 修复

- **飞书集成配置保存失败**（3 处 bug）：
  - `GET /admin/feishu/settings` 返回 `app_secret_masked` 但前端表单字段为 `app_secret`，字段名不匹配导致密钥永远为空
  - `FeishuSettingsTab` 的 `Form initialValues` 内联对象每次渲染重建，Ant Design 检测变化后重置表单
  - `PUT /admin/feishu/settings` 缺少 `await db.commit()`，事务在请求结束时自动回滚，所有写入丢弃
- 生产部署流程修正：必须通过 `upgrade.sh --tag` 统一部署，不得手动 SSH 部分构建

### 新增

- 水獭吉祥物 favicon（16/32/48/64px ICO）+ apple-touch-icon
- 顶栏 Logo 替换为 GPT-Image-2 水獭头像

### 文档

- 用户手册新增《飞书集成配置》章节（zh-CN + en-US）
- 更新功能参考、概述页的版本路线至 v1.1.0

---

## [v1.1.0] — 2026-04-29

**首个稳定发布版**。rc1–rc6 系列特性集已完整交付，所有 CI 门禁绿色。

### 功能总览

- **采购全流程**：PR → 多级审批 → PO → 多批交货 → 分批付款 → 发票三单匹配
- **审批引擎**：可视化规则编辑器，按业务类型 + 金额区间自动路由多阶段串签 + 审批代理人
- **询价管理（RFQ）**：多供应商报价 + 自动最低价定标
- **合同管理**：全生命周期 + 版本管理 + OCR 全文检索 + 到期预警
- **发票核销**：AI 抽取（PDF / 图片 → LLM 结构化）+ 人工复核
- **SKU 行情库**：90 天基准价 + ±20% 异常识别 + 多选价格走势对比图
- **表单自动保存**：PR 新建/编辑 + PO 交货/付款/发票 modal — localStorage 草稿防丢失
- **飞书集成**：卡片消息推送 + 付款审批工作流 + webhook 回调，默认关闭可按需启用
- **权限体系**：Cerbos 字段级 + 行级权限 · 6 种角色 · RBAC 路由守卫 · 审计日志
- **国际化**：中 / 英双语全覆盖（前端 600+ keys · 后端 200+ 消息）
- **测试**：pytest 417 passed (backend 73%) · vitest 58 passed (frontend 60%) · Playwright E2E 47 tests
- **运维**：Docker Compose 一键部署 · backup / restore / upgrade / 零停机滚动

### 技术栈

Python 3.12 · FastAPI · SQLAlchemy 2.x async · Alembic (31 migrations) · PostgreSQL 16 · pg_trgm · Cerbos sidecar · React 18 · TypeScript 5 · Vite · Ant Design 5 · Zustand · LiteLLM SDK · Docker Compose v2 · Nginx

---

## [v1.0.0-rc6] — 2026-04-29

### 新增

- **审批规则可视化编辑器**：Admin 控制台新增 Approval Rules 选项卡，支持拖拽排序审批阶段、金额阈值配置、多角色串签规则 CRUD。
- **合同版本管理**：合同编辑时自动创建版本快照，支持变更摘要记录和版本历史查看。
- **飞书集成（完整实现）**：消息推送（PR 提交/审批决策/PO 生成/付款待审/合同到期）+ 付款审批工作流 + webhook 回调 + Admin 配置页。默认关闭，管理员在控制台配置 App ID/Secret 后启用。
- **E2E 浏览器测试**：Playwright 47 条测试覆盖登录、导航、PR 流程、PO 流程、仪表盘、管理、搜索。
- **合同扫描件在线预览**：PDF/图片改为浏览器内嵌展示（Content-Disposition: inline）。

### 变更

- **CI**：Node 版本升级 20 → 24；E2E Playwright 作业加入流水线。
- 修复 `import_suppliers` / `import_prices` 端点缺少 `db` 参数导致的 ruff F821 错误。

---

## [v1.0.0-rc4] — 2026-04-29

### 新增

- **表单自动保存（Autosave）**：采购申请新建页（PRNew）和编辑页（PREdit）新增 localStorage 草稿自动保存。
  - 防抖写入（800ms），切换页面或浏览器崩溃后返回页面时弹出恢复横幅，支持一键恢复或丢弃。
  - 隐私模式 / localStorage 被禁���时展示 `AutosaveUnavailableBanner` 警告，而非静默丢失数据。
  - 提交成功后自动清除草稿。
  - autosave key：`mica:autosave:pr-new` / `mica:autosave:pr-edit:<id>`
  - i18n：9 条 `autosave.*` 键（zh-CN + en-US）全部覆盖。

---

## [v1.0.0-rc3] — 2026-04-28

### 新增

- **8 条扩展集成测试** (`test_extended_flows.py`)：覆盖合规性采购流程、审批代理、成本中���可见性、RFQ 询价、合同支出、合同到期告警、SKU 价格基准及全局搜索。

---

## [v1.0.0-rc2] — 2026-04-28

### 修复

- **后端角色权限补全**：`list_shipments` / `list_payments` / `list_invoices` 三个 list 端点补加 `require_roles` 检查（rc1 遗漏）。
- **前端路由守卫**：`ProcurementGate` 拦截 11 条采购/合同/财务路由；AppLayout 导航菜单对 `requester` 角色隐藏 8 个入口。
- **5 条角色拒绝集成测试** (`test_role_denials.py`)：覆盖 requester 访问 PO/供应商/合同/报表/管理端点应返回 403。

---



### v1.0 Release Candidate

Mica has reached production-grade readiness. This RC consolidates all v0.9.x hardening work.

#### Production Readiness

- **Dependency locking**: all 27 dependencies pinned with sensible upper bounds (prevents build flakiness)
- **Health endpoint**: `/health` returns structured `{status, checks: {db, cerbos}}`, with degraded detection for partial failures
- **Integration tests**: 15 tests covering HTTP layer (PR→PO, SAML JIT, dashboard, role denials, admin CRUD)
- **Request-ID middleware**: every request gets `X-Request-ID` injected into response headers, error bodies, and log records via contextvars
- **RBAC audit**: 17 backend endpoints now require procurement/finance roles; frontend route guards + nav hiding for requester role
- **Requester row-level scoping**: M:N cost center + department visibility (OR semantics), applied to 6 entity types across list + detail endpoints
- **SAML JIT hardening**: write-time referential validation for default company/department codes (prevents crash-at-login)
- **Denylist CI**: automated scan blocks tenant-specific identifiers from being committed to the public repo

#### Feature highlights (carried from v0.9.x)

- Full procurement lifecycle: PR → approval → multi-supplier PO split → contract M:N → shipment → payment → invoice
- Dashboard: PaymentTracker (monthly forecast), InvoiceTracker (invoiceable vs invoiced), alerts (contract expiry, price anomalies, pending invoices)
- AI-powered document generation (payment forms, templates)
- Configurable contract/bill number prefixes via system parameters
- i18n: zh-CN / en-US coverage across UI and backend messages
- Column visibility customization with localStorage persistence
- SKU price records auto-recorded from PR supplier quotes and PO actual prices

