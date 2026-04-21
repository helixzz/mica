<!-- version: 0.5.0; updated: 2026-04-21 -->

# 04 · 功能参考

本章按功能模块索引每个可执行动作的入口、约束和常见用法。遇到具体操作疑问时，建议先定位到对应模块的小节，再查阅下方表格与要点；如仍有疑问，请跳转到 [05 · 常见问题](./05-faq.md)。

---

## 身份与登录

| 能力 | 状态 | 说明 |
|---|---|---|
| 本地密码登录 | ✅ 当前主力 | 用户名 + 密码，后端颁发访问令牌 |
| SAML SSO（ADFS） | 🚧 规划中 | 按需对接企业身份源 |
| 语言切换 | ✅ | 右上角菜单切换中文 / English，选择后持久化到浏览器 |

**语言检测优先级**（`frontend/src/i18n/index.ts:23-27`）：

1. `localStorage`（key: `mica.locale`）
2. `cookie`（`mica_locale`）
3. `navigator.language`（浏览器语言）
4. HTML `<html lang="...">` 标签
5. 兜底 `zh-CN`

用户一旦在界面上手动切换语言，偏好会被写回 localStorage 与 cookie，此后所有会话均按该语言渲染。

---

## 采购申请 (PR)

采购申请是所有采购动作的起点。提交后自动触发审批引擎，审批通过方可转为订单。

### 状态流转

| 状态 | 含义 | 允许的下一步 |
|---|---|---|
| `DRAFT` | 草稿 | 编辑、删除、提交 |
| `SUBMITTED` | 已提交待审批 | 审批（批准 / 退回 / 拒绝）、撤回 |
| `APPROVED` | 审批通过 | 转为 PO、作废 |
| `RETURNED` | 被退回 | 重新编辑 → 再次提交 |
| `REJECTED` | 已拒绝（终结） | 仅查看 |
| `CANCELLED` | 已作废（终结） | 仅查看 |
| `CONVERTED` | 已转为 PO（终结） | 查看关联 PO |

### 编辑约束

- **只有 `DRAFT` 状态可以编辑**（`backend/app/api/v1/purchase.py:120-121`）。
- 被退回后，状态会切回可编辑态，修改后重新提交即进入新一轮审批流。
- 已提交的 PR 不能直接改金额，需先撤回 → 修改 → 重新提交。

### 明细行字段

每行（`schemas.PRItemIn`）字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `line_no` | int | 行号（从 1 递增） |
| `item_id` | UUID?（可选） | 若引用 SKU 主数据则填 |
| `item_name` | string | 物料名称（必填） |
| `specification` | string? | 规格型号 |
| `supplier_id` | UUID?（可选） | 预选供应商 |
| `qty` | decimal | 数量（> 0） |
| `uom` | string | 计量单位（台 / 件 / kg…） |
| `unit_price` | decimal | 单价 |

> 单行金额 = `qty × unit_price`；PR 总金额自动汇总所有行。

### 提交动作

点击"提交审批"：
1. 校验字段完整性；
2. 创建审批实例（调用审批引擎，见下节）；
3. PR 状态 `DRAFT → SUBMITTED`；
4. 待办出现在指定审批人的"待办审批"页。

---

## 审批引擎

### 总体规则

- **v0.5 起支持多级串签**。通过 `approval_rules` 按 `biz_type + 金额区间 + stages` 配置多阶段审批，种子规则复现原单级/两级行为。多级规则的前一阶段 `approved` 自动激活下一阶段的 `waiting` 任务；任一阶段 `rejected` 则后续阶段置 `skipped`。
- **审批代理人**（v0.5）：审批人出差期间可将 approval 任务临时路由给受托人（`approver_delegations`）。
- 会签 / 并行审批（同一阶段多人同时审批）属于 v0.7+ 范畴。

### 金额路由表

审批人根据 PR 总金额自动解析（`backend/app/services/approval.py:20-46`）：

| PR 金额 | 路由规则 |
|---|---|
| `< ¥100,000` | 提交人同部门的**部门负责人**（`dept_manager`）；若该部门无部门负责人，则回退给 `admin` |
| `≥ ¥100,000` | 公司的**采购经理**（`procurement_mgr`）；若未配置，则回退给同部门部门负责人；再回退给 `admin` |

> 阈值 `Decimal("100000")` 为硬编码，单位为该公司的本位币（当前默认 CNY）。

### 审批动作

| 动作 | 结果 |
|---|---|
| **批准** | PR 状态 → `APPROVED`；后续可转为 PO |
| **退回** | PR 状态 → `RETURNED`；提交人可重新编辑再提交 |
| **拒绝** | PR 状态 → `REJECTED`（终结，不可撤销） |

每次决定都会记录决定人、决定时间与批注，写入审批任务与 PR 的 `decision_comment` 字段。

### 待办查询

- 后端端点：`GET /api/v1/approval/pending`
- 前端入口：左侧菜单"待办审批 / Pending Approvals"
- 返回当前登录用户名下所有未完成的审批任务，按创建时间倒序。

---

## 采购订单 (PO)

### 生成方式

- PO **只能从 PR 转换生成**。
- 前置条件：PR 状态为 `APPROVED`，且明细行中**只涉及单一供应商**。多供应商的 PR 需拆分为多个 PR（或等待后续版本支持多 PO 拆分）。

### 进度冗余字段（6 项）

PO 表冗余 6 个统计字段，避免每次查询都重算：

| 字段 | 含义 |
|---|---|
| `qty_received` | 累计已收货数量 |
| `amount_paid` | 累计已付款金额 |
| `amount_invoiced` | 累计已开票金额 |
| `receive_progress_pct` | 收货进度百分比 |
| `payment_progress_pct` | 付款进度百分比 |
| `invoice_progress_pct` | 开票进度百分比 |

上述字段在发生交货 / 付款确认 / 发票创建时由后端同步回写。

### 状态

| 状态 | 触发条件 |
|---|---|
| `CONFIRMED` | 从 PR 转换成功，尚未收货 |
| `PARTIALLY_RECEIVED` | 至少一次收货，但 `qty_received < 订单总数` |
| `FULLY_RECEIVED` | `qty_received == 订单总数` |

状态完全由交货批次驱动，运营人员无需手动切换。

### 进度端点

- `GET /api/v1/purchase-orders/{id}/progress`：返回三条进度（收货 / 付款 / 开票）的百分比与明细，前端详情页的三条进度条直接由此驱动。

---

## 合同（轻量归档）

当前版本合同仅作为**元数据记录**使用，便于后续审计和资料检索。

| 字段 | 说明 |
|---|---|
| `contract_number` | 合同编号 |
| `title` | 合同标题 |
| `amount` | 合同金额 |
| `signed_date` | 签署日 |
| `effective_date` | 生效日 |
| `expire_date` | 到期日 |
| `remarks` | 备注 |

- 合同关联到 **PO + 供应商**。
- **扫描件归档 + OCR 全文检索已在 v0.4.2 实现**，详见本章"合同扫描件归档与全文检索"。

---

## 交货批次 (Shipment)

### 多批次支持

- 每个 PO 可以分多次交货，`batch_no` 从 1 递增。
- 无需在订单阶段预设拆分数量，按实际到货情况录入即可。

### 自动回写

每次创建交货批次，后端自动完成：

1. 累加对应行的 `qty_received`；
2. 重新计算 PO.status：
   - 若 `qty_received < 订单总数` → `PARTIALLY_RECEIVED`
   - 若 `qty_received == 订单总数` → `FULLY_RECEIVED`
3. 回写 PO.receive_progress_pct。

### 序列号录入

- 字段：`shipment_items.serials[]`（字符串数组）。
- 主要用于 IT 硬件资产归档（电脑、网络设备等需唯一追溯的物件）。
- 非硬件类采购可留空，系统不强制校验数量与序列号个数一致。

---

## 付款 (Payment)

### 创建与确认两段式

| 场景 | 操作 |
|---|---|
| 创建时已付款 | 创建付款记录时直接填写 `payment_date`，状态即为"已付款" |
| 创建时仅记账 | `payment_date` 留空；之后在详情页点击"标记已付款"（`confirm` 按钮）完成确认 |

确认成功后：
- 付款状态 → `PAID`；
- 回写 PO.amount_paid 与 payment_progress_pct。

### 范围与限制

- 当前**仅作为内部台账记录**，不与任何外部支付通道（银行接口 / 财务系统）对接。**v0.5 起**支持"导出 Excel"生成付款明细表给财务人工对账 / 录入网银。
- 外部联动（飞书付款审批卡片、财务系统 API 推送）属于 v0.6+ 规划。

---

## 发票 (Invoice)

发票是本系统中逻辑最复杂的模块，以下要点最关键。

### 跨 PO 支持（重点）

- **一张发票可以包含多个 PO 的行**。例如：供应商一次性为本月 3 个 PO 开具一张汇总发票，无需拆成 3 张录入。
- 每一行通过 `po_id + po_item_id` 关联具体的 PO 行；未关联时系统视为未匹配行。

### Header 字段

| 字段 | 说明 |
|---|---|
| `internal_number` | 系统内部编号（自动生成） |
| `invoice_number` | 发票号（供应商开具） |
| `invoice_date` | 开票日 |
| `supplier_id` | 开票方供应商 |
| `total_amount` | 发票总额（= Σ subtotal + Σ tax_amount） |
| `currency` | 币种 |
| `status` | `MATCHED` / `PENDING_MATCH` |

### Line 字段

每行（`invoice_lines`）：

| 字段 | 说明 |
|---|---|
| `line_type` | `product` / `freight` / `adjustment` / `tax_surcharge` / `note` |
| `po_id` + `po_item_id` | 关联的 PO 行（product 类型才需要） |
| `qty`, `unit_price` | 数量与单价 |
| `subtotal` | `qty × unit_price` |
| `tax_rate`, `tax_amount` | 税率与税额（每行独立） |

> **发票总额 = Σ subtotal + Σ tax_amount**，不单独在 header 保留税额合计。

### 状态与匹配规则

| 状态 | 判定 |
|---|---|
| `MATCHED` | 所有 `product` 行都有 `po_item_id` **且** 累计 `qty × unit_price` **不超**对应 PO 行剩余额度 |
| `PENDING_MATCH` | 存在未匹配 product 行，或匹配后存在超额行 |

### 验证返回

创建 / 更新发票时，后端同步返回 `validations[]` 数组：

```json
{
  "severity": "ok" | "warn" | "error",
  "code": "...",
  "message": "...",
  "line_no": 2
}
```

**重要**：超额**不阻断保存**（软警告），只会把发票标记为 `is_fully_matched = false`，以便财务手工复核。真正阻断的是 `error` 级别（如缺失必填字段、币种不一致）。

---

## AI 辅助功能

当前启用的 AI 能力由 `ai_feature_routings` 表配置，内置以下几项：

| feature_code | 用途 | 前端入口 |
|---|---|---|
| `pr_description_polish` | PR 业务说明润色 / 补齐 | PR 编辑页"AI 润色"按钮 |
| `sku_suggest` | 根据描述推荐 SKU | PR 明细"智能推荐"按钮 |

### 前后端交互

- **SSE 流式响应**：后端以 `text/event-stream` 流式推送 token，前端组件 `AIStreamButton` 边接收边展示。
- 用户可中途取消；取消后已产生的 token 仍会计入成本（见下）。

### 默认模型

- 两个 feature 默认路由到 `demo-mock` 模型（`backend/app/services/seed.py:130-145`）。
- `demo-mock` 仅返回占位文本，便于开发联调。**真实 LLM 对接需管理员在控制台的"LLM 模型"Tab 中配置**——详见下文"管理员控制台"。

### 成本追踪

- 每次调用无论成功或失败，都会写入 `ai_call_logs` 表，字段包括：
  - 调用耗时、输入 / 输出 token 数、状态、错误码；
  - 关联的业务单据（如触发它的 PR id）；
  - 使用的模型 id 与 feature_code。
- 管理员可在控制台的"AI 调用日志"Tab 中查看聚合统计与每条调用明细。

---

## 发票文件上传与 AI 智能提取

登记发票时，**必须上传至少一份发票原件**（PDF / OFD / XML / 图片），作为入账凭证。系统会自动从文件中识别发票关键字段并预填到表单，你只需核对。

### 必填约束

- 提交发票登记时若附件为空，后端接口直接返回 HTTP 422，前端会提示"请上传发票原件"。
- 这是硬约束：任何发票都必须有至少一份原件在系统中留档，便于后续审计与下载。

### 支持的格式

| 格式 | 说明 |
|---|---|
| **PDF** | 常见电子发票 / 扫描件 |
| **OFD** | 国产电子发票版式（ZIP 结构） |
| **XML** | 数电票原件 XML |
| **JPG / PNG / TIFF** | 扫描件或手机拍照的图片 |

### 提取策略（6 级分层）

系统按**成本从低到高**逐级尝试，只要前一级识别成功，后续昂贵的步骤就不会触发——最大限度节省 AI 调用开销：

1. **XML 原件直接解析**：数电票 XML 结构化数据，置信度 ~99%，无需 AI。
2. **OFD ZIP 包解析**：解开 OFD 内嵌的 XML 元数据，电子发票常见路径。
3. **PDF 内嵌 XML 附件**：部分数电票 PDF 把 XML 原件作为附件嵌在 PDF 内部，直接抽取。
4. **PDF 文本层 + 正则**：旧版电子发票 PDF 有可选中的文本层，走规则匹配。
5. **LLM Vision**：扫描件、图片、无文本层的 PDF 进入视觉模型识别；**需管理员在控制台为 `invoice_extract` 场景配置视觉模型**（如未配置则此级跳过）。
6. **手动填写**：任何一级失败或识别字段有疑问时，所有字段均可手动编辑改写，作为兜底。

### 提取字段

- 发票号码、开票日期
- 销方名称 + 税号
- 购方名称 + 税号
- 金额（不含税 / 含税）、税额、税率
- 明细行（物料名称、数量、单价、金额）

### 置信度提示

识别成功后，按钮右侧会显示 "AI 来源 · 置信度 X%" 的小标签（如 `XML · 99%` / `Vision · 86%`）。你可以一眼判断当前数据的可信程度，决定是否对照原件人工核对。

> **说明**：实际识别精度取决于发票版式与模型能力，通常在 85%–95% 区间浮动，扫描质量差或版式少见的发票会更低。**识别结果永远可以手动修改**。

### 附件存储

- **SHA-256 内容哈希去重**：同一张发票 PDF 重复上传会指向同一份物理文件，不会重复入库占用空间。
- **原子写入**：上传过程中断不会产生半截文件，避免坏数据。

### 下载原件

- 通过**一次性 token** 下载：前端调用 `GET /documents/{id}/token` 换取一个有效期 1 小时的 token，再用该 token 调用 `GET /documents/download/{token}` 取到原文件。
- token 使用后立即失效，防止链接被转发长期滥用。

### API 端点清单（面向技术用户）

| 端点 | 说明 |
|---|---|
| `POST /documents/upload` | 上传附件，返回文档 id 与哈希 |
| `POST /ai/invoice-extract` | 对已上传的文档触发字段提取，返回结构化结果 + 置信度 |
| `GET /documents/{id}/token` | 生成 1 小时有效的下载 token |
| `GET /documents/download/{token}` | 凭 token 下载原件（一次性） |

---

## 管理员控制台

v0.4.1 起，管理员可通过前端界面完成 LLM 模型配置、AI 路由、用户管理、日志查询等运维动作，不再需要直接操作数据库或 `.env`。**v0.5 新增两个标签页**：

- **系统参数**（`system_params`）：14 项业务阈值从硬编码搬到 DB，可从 UI 直接编辑：审批金额阈值、JWT/刷新令牌有效期、SKU 基准价窗口、SKU 异常阈值百分比、合同到期提醒窗口、上传文件最大尺寸、分页默认页大小、审计日志默认回溯天数等。每个参数带最小/最大边界校验、单位标注、中英双语描述、"重置到默认"按钮、"已修改"徽标。
- **主数据管理**（扩展）：除原有只读视图，v0.5 新增 `POST / PATCH / DELETE` 接口支持供应商、物料、公司、部门的增删改查。部门支持 `parent_id` 树层级 + 循环检测。所有写操作自动记入审计日志。

### 访问入口

左侧菜单 **系统管理 Admin Console**——**仅 `admin` 角色可见**，其他角色既看不到菜单，也无法通过 URL 直接访问（后端接口同样拒绝）。

### 六个功能 Tab

#### 1. 系统参数（System Settings）

只读展示当前运行时配置：应用版本、默认语言、JWT 过期时间、媒体存储根路径等。**敏感配置（`SECRET_KEY`、数据库密码等）不会出现在 UI 中**——这些只能通过 `.env` 或部署脚本管理。

#### 2. LLM 模型（LLM Models）

对 `ai_models` 表做完整 CRUD 管理，是控制台中最核心的 Tab。

| 字段 | 说明 |
|---|---|
| `name` | 模型在系统内的显示名（如"通义千问 Max") |
| `provider` | 供应商标识：`openai` / `dashscope` / `volcengine` / `mock` 等 |
| `model_string` | LiteLLM 格式字符串，如 `openai/gpt-4o`、`dashscope/qwen-max` |
| `modality` | `text` / `vision` / `ocr` / `embedding` |
| `api_base` | 自定义网关地址（可选） |
| `api_key` | 使用 Fernet 加密存储；UI 中脱敏显示为 `sk-12****xxxx` |
| `timeout` | 单次调用超时时间（秒） |
| `priority` | 优先级，影响降级链顺序 |
| `is_active` | 是否启用 |

**测试连接 Test Connection** 按钮：后端向该模型发起一个最小 completion 请求，返回：

- `success`：连通性正常 / 异常
- `latency`：往返耗时（毫秒）
- `model_response`：真实返回内容片段（便于核对是否对的上模型）
- `error`：失败时的错误信息

新增或修改模型后，强烈建议点一次测试连接，避免等到用户触发业务 AI 时才发现 key 错了。

#### 3. AI 场景路由（AI Routing）

为每个 `feature_code` 绑定要使用的模型。当前 feature 清单：

- `pr_description_polish` — PR 业务说明润色
- `sku_suggest` — SKU 智能推荐
- `invoice_extract` — 发票字段识别（视觉）

每条路由可配置：

- **主模型**：默认使用的模型
- **降级链**：主模型失败时按顺序尝试的备选模型
- `temperature` / `max_tokens` 等生成参数

#### 4. 用户管理（Users）

列出所有用户，支持新增用户、重置密码、查看最后登录时间。

#### 5. AI 调用日志（AI Call Logs）

查询 `ai_call_logs` 表。

- **顶部卡片**：按 `feature_code` 聚合展示 7 日内的**调用量、token 总量、平均延迟**。
- **下方列表**：每条调用的用户、模型、输入/输出 token、延迟、`status`（`success` / `error`）、`error message`。可按时间、feature、用户筛选。

#### 6. 审计日志（Audit Logs）

查询 `audit_logs` 表。支持按**事件类型前缀**（如 `invoice.`）、**资源类型**（如 `supplier`）、**时间范围**多条件过滤。列表展示时间、操作人、事件类型、资源类型 + ID、备注。

### 典型使用场景

以下从管理员视角讲，不讲技术细节：

- **"我需要把 AI 模型从 mock 切换到真实的通义千问"**
  LLM 模型 Tab → **新增 New** → 填 `model_string = dashscope/qwen-max`、填 `api_key` → 点**测试连接 Test Connection** 确认返回成功 → 保存 → 切到 AI 场景路由 Tab，把 `pr_description_polish` 的主模型改为新增的这条。

- **"财务反馈 AI 识别发票不准"**
  AI 调用日志 Tab → 筛选 `feature_code = invoice_extract` → 关注低置信度或 `error` 的记录 → 判断是模型问题还是发票扫描质量问题 → 必要时在 LLM 模型 Tab 新增一个更强的视觉模型并在 AI 场景路由 Tab 升级绑定。

- **"有人改了供应商数据我要查是谁"**
  审计日志 Tab → 筛选 `resource_type = supplier` → 按时间范围收敛 → 看操作人与事件类型（如 `supplier.updated`）。

---

## 权限矩阵（综合）

下表按资源 × 角色汇总字段级可见性（来源：`backend/app/core/field_authz.py`）。`*` 表示该角色可见全部字段；数字表示该角色仅可见这么多个字段（其余字段在接口层被剔除）。

| 资源 / 角色 | `admin` | `it_buyer` | `dept_manager` | `finance_auditor` | `procurement_mgr` |
|---|---|---|---|---|---|
| `purchase_requisition` | * | * | * | 18 字段 | * |
| `purchase_order` | * | 15 字段 | 12 字段 | * | * |
| `payment_record` | * | 12 字段 | 8 字段 | * | * |
| `invoice` | * | 10 字段 | 8 字段 | * | * |

> 字段级读权限在 API 序列化层生效；写权限由各接口单独校验。完整可见字段清单见源码 `FIELD_PERMISSIONS` 字典。若需更细粒度的行级 / 属性级策略，请参考 v0.6+ Cerbos 独立 sidecar 规划（目前策略内嵌于 `core/field_authz.py`）。

---

## SKU 行情库与价格异常预警

追踪每个物料的历史报价，自动计算基准价，对异常报价自动预警。

### 什么时候用

- 采购员想知道"这个价格合理吗"——查最近 90 天的均价、中位、最低、最高
- 每月例行收集供应商报价——直接录入系统，沉淀为长期趋势
- 下一次新报价明显偏离历史水平时系统自动提示

### 三类数据

| 数据 | 作用 | 谁写入 |
|:---|:---|:---|
| **报价记录（Price Record）** | 某时某供某物的具体价格 | 采购员手工录入 / 实际成交的 PO 自动回填（v0.7+） |
| **基准价（Benchmark）** | 滚动窗口内的统计（均值、中位、最低、最高、标准差、样本数） | 系统自动计算，每录入新价格时刷新 |
| **异常记录（Anomaly）** | 偏离基准 ≥ 20% 的报价自动标记 | 系统自动创建，采购员确认后归档 |

### 页面与操作

- 菜单：**SKU 行情 (SKU Pricing)**
- 入口行为：
  - 顶部橙色预警条列出**未确认的异常记录**，每条都可展开"物料 / 基准均价 / 本次价格 / 偏离 / 严重度"，操作员点"已知悉"归档
  - 中部"选择物料"下拉 → 选择 SKU 后显示 **5 项统计 + 时间序列表**
  - 底部"近期全部报价"列出所有物料最新 200 条
- 按钮 **录入报价 Record Price**：填 SKU、供应商（可选）、价格、日期、来源。来源分四种：`manual`（手工）/ `quote`（供应商报价）/ `actual_po`（实际订单）/ `market_research`（市场调研）
- 录入后若偏离基准 ±20% → 系统返回 `warning`，±40% → `critical`

### 基准价如何计算

- 默认窗口 **90 天**（可配置）
- 该窗口内的所有 `price_record` 参与统计
- 每次录入新价格时，系统实时重算：`avg_price / median_price / stddev / min / max / sample_size`
- 样本数 < 3 时**不触发异常检测**，避免噪音

### 规划（v0.6+）

- PO 成交价自动回填（`source_type=actual_po`），减少手工录入
- LLM 辅助 SKU 归一化（"戴尔 R750" / "Dell PowerEdge R750" 判为同一 SKU）
- 按供应商分组的价格趋势图（目前只有全局趋势）
- 每日 / 每周的异常汇总报表

---

## 合同扫描件归档与全文检索

把签署后的纸质 / PDF 合同扫入系统，自动 OCR 识别文本，后续可以按任意关键字搜索。

### 什么时候用

- 合同签署后需要把纸质件或电子件作为正式凭证入库
- 日后对账、争议处理、合规审计要翻出某份合同——搜关键词比翻文件夹快得多
- 合同快到期了，系统主动提醒续签或归档

### 支持的格式

| 格式 | 说明 |
|:---|:---|
| PDF | 文本层 PDF 优先用 `pdfplumber` 提取，扫描 PDF 走 LLM Vision |
| OFD | 国产电子发票版式，ZIP 包内 XML |
| XML | 电子发票原件，100% 结构化解析 |
| JPG / PNG / TIFF | 扫描件走 LLM Vision |

### 页面与操作

- 菜单：**合同 (Contracts)**
- 列表页顶部三个区块：
  - **搜索框**：输入关键字后，系统对"合同标题 / 合同号 / 扫描件 OCR 文本"做不分大小写的模糊匹配；匹配命中处以 Tag 形式展示上下文（`ocr:…片段…`）
  - **30 天内到期**预警卡：橙色背景，列出即将到期的合同供续签决策
  - **全部合同**表格：点合同号进详情页
- 合同详情页：
  - 顶部合同信息（标题、金额、签署日、生效日、到期日、版本、备注）
  - **合同扫描件归档**区块，右上"上传扫描件（自动 OCR）"按钮
  - 上传后系统自动调用 AI 提取文本并存入数据库，列表中显示 "OCR X chars" 标签表示已索引的字符数
  - 每个附件可"下载"（生成一次性 token，新标签打开）

### 扫描件安全

- 文件经 SHA-256 内容哈希去重
- 下载走一次性 token，1 小时过期，用后立即失效
- 附件元数据（文件名、类型、大小）与合同多对多关联，支持一份文件关联多个合同

### 检索机制（当前实现）

- **v0.5 起**：PostgreSQL `pg_trgm` 扩展 + `tsvector` 生成列 + GIN 索引，支持中文子串匹配 + 排名（`ts_rank`）+ 摘要高亮（`ts_headline`）。全局搜索端点 `GET /api/v1/search?q=&types=` 跨 PR/PO/合同/发票/供应商/物料统一查询，结果分桶返回。
- **v0.7+ 升级计划**：PG `zhparser` 中文分词（需自定义 PG 镜像），支持更准确的中文词边界识别与精确短语 / 布尔查询。

### 合同到期提醒

- API：`GET /contracts-expiring?within_days=30`（`within_days` 默认从系统参数 `contract.expiry_reminder_days` 读取）
- UI：合同列表页自动显示 30 天内到期的 active 状态合同
- **仪表盘集成（v0.5 已上线）**：合同到期 30 天前自动在通知中心推送给合同所有者 + 采购经理 + 管理员。通知提醒窗口可从 Admin 控制台"系统参数" → `contract.expiry_reminder_days` 调整。

---

## 规划中的功能

以下功能**尚未在当前版本提供**，按里程碑排列：

- **v0.6**
  - 飞书集成：消息通知 + 审批卡片联动（等 App ID + Secret）
  - 单元测试覆盖 + CI 流水线
  - 真实 LLM 模型接通演示（通义 / 豆包 / DeepSeek / OpenAI）
- **v0.6+**
  - Cerbos sidecar 化（当前策略内嵌于 `core/field_authz.py`）
  - 批量导入（供应商 / 物料 / 历史报价 Excel 导入）
  - PO 成交价自动回填到 SKU 价格库
- **v0.7+**
  - PostgreSQL zhparser 中文分词（升级当前 pg_trgm 方案）
  - 云服务商账单自动生成月度 PO
  - 飞书付款申请端到端自动化
  - 多级审批 DSL 的可视化编辑器（当前可编辑 JSON 规则）
- **按需**
  - ADFS SAML 真实对接（骨架已就绪）

如需优先支持某项功能或提交需求，请联系系统管理员。
