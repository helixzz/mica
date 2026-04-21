<!-- version: 0.4.0; updated: 2026-04-21 -->

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

- **当前版本为单级审批**（v0.4 限制）。每个 PR 仅生成一个审批任务，审批人作出决定后审批流即结束。
- 多级 / 会签 / 并行审批属于后续版本范畴。

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
- **当前不支持上传扫描件 / PDF**；扫描件归档 + OCR 全文检索将在 v0.6 提供（见章末"规划中的功能"）。

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

- 当前**仅作为内部台账记录**，不与任何外部支付通道（银行接口 / 财务系统）对接。
- 外部联动（飞书付款审批、财务系统推送）属于 v0.7 规划。

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

当前启用的 AI 能力由 `ai_feature_routings` 表配置，v0.4 内置两个：

| feature_code | 用途 | 前端入口 |
|---|---|---|
| `pr_description_polish` | PR 业务说明润色 / 补齐 | PR 编辑页"AI 润色"按钮 |
| `sku_suggest` | 根据描述推荐 SKU | PR 明细"智能推荐"按钮 |

### 前后端交互

- **SSE 流式响应**：后端以 `text/event-stream` 流式推送 token，前端组件 `AIStreamButton` 边接收边展示。
- 用户可中途取消；取消后已产生的 token 仍会计入成本（见下）。

### 默认模型

- 两个 feature 默认路由到 `demo-mock` 模型（`backend/app/services/seed.py:130-145`）。
- `demo-mock` 仅返回占位文本，便于开发联调。**真实 LLM 对接需管理员在控制台配置**——该控制台属于 v0.5 规划。

### 成本追踪

- 每次调用无论成功或失败，都会写入 `ai_call_logs` 表，字段包括：
  - 调用耗时、输入 / 输出 token 数、状态、错误码；
  - 关联的业务单据（如触发它的 PR id）；
  - 使用的模型 id 与 feature_code。
- 管理员可据此做成本核算与异常告警（v0.5 控制台提供可视化）。

---

## 权限矩阵（综合）

下表按资源 × 角色汇总字段级可见性（来源：`backend/app/core/field_authz.py`）。`*` 表示该角色可见全部字段；数字表示该角色仅可见这么多个字段（其余字段在接口层被剔除）。

| 资源 / 角色 | `admin` | `it_buyer` | `dept_manager` | `finance_auditor` | `procurement_mgr` |
|---|---|---|---|---|---|
| `purchase_requisition` | * | * | * | 18 字段 | * |
| `purchase_order` | * | 15 字段 | 12 字段 | * | * |
| `payment_record` | * | 12 字段 | 8 字段 | * | * |
| `invoice` | * | 10 字段 | 8 字段 | * | * |

> 字段级读权限在 API 序列化层生效；写权限由各接口单独校验。完整可见字段清单见源码 `FIELD_PERMISSIONS` 字典。若需更细粒度的行级 / 属性级策略，请参考 v0.5 Cerbos 集成规划。

---

## 规划中的功能

以下功能**尚未在当前版本提供**，按里程碑排列：

- **v0.5**
  - 管理员控制台（LLM 模型与路由配置、系统参数、用户 / 角色管理）
  - 发票文件上传 + AI 视觉 OCR（自动抽取抬头 / 税号 / 金额）
  - Cerbos 引擎接入 + 行级 / 属性级细粒度权限
- **v0.6**
  - 合同扫描件归档 + OCR 全文检索
- **v0.7**
  - 飞书集成：消息通知 + 付款审批联动
- **v0.8**
  - SKU 行情库与价格异常预警
- **按需**
  - ADFS SAML 真实对接

如需优先支持某项功能或提交需求，请联系系统管理员。
