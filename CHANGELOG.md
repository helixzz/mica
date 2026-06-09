# Changelog

All notable changes to Mica will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [v1.31.1] — 2026-06-09

### 新增

- **侧边栏可收起**：桌面端 Header 左上角新增展开/收起按钮（旁边那个汉堡图标会随状态切换为 fold/unfold 图标）。收起后侧边栏从 220px 缩到 80px，仅显示菜单图标，鼠标悬停可看到完整名称。状态写入 `localStorage.mica.sider_collapsed`，刷新后保持
- 收起时 Logo 文字隐藏，只显示水獭头像图标，给内容区让出更多空间

---

## [v1.31.0] — 2026-06-09

### 新增

- **POItem 编辑/删除**：PO 详情页"物料"列表新增"操作"列。可修改任意行的物料名称 / 规格 / 数量 / 单价，或删除整行
  - **PATCH /po-items/{id}**：admin/it_buyer/procurement_mgr 可编辑。已开发票的行禁止改数量/单价；新数量不得低于已到货数量
  - **DELETE /po-items/{id}**：admin/it_buyer/procurement_mgr 可删除。有到货 / 发票 的行禁止删除
  - 编辑/删除后自动重算 PO 总额；同步调整该行关联的 fulfillment_link.qty_contribution；触发 PR 状态重新计算
- **降配履约时可单独定价**：自定义拆分对话框新增"本次单价"列。降配版本通常便宜——现在可在拆分时直接输入实际成交单价，不再被 PR 原价绑死。`PRConvertSpec.unit_price` 可选；不指定则继承 PR 行原价
  - 后端 `PRConvertSpecIn` schema 增加 `unit_price` 字段
  - 创建的 POItem.unit_price + amount 使用拆分时输入的单价；SKU 价格记录也按实际成交价写入

### 修复

- **数据修复**：清理 PO-2026-0019 上 v1.30.0 hotfix 之前 3 个失败请求遗留的重复 POItem 行（每条 amount 5,160 万元，导致 PO 合计虚高 1.5 亿）。重新编号 line_no，重算 total_amount。该问题已通过 v1.30.1 hotfix 解决，本版补做数据清理 + 提供前端编辑/删除能力让用户自行处理类似情况

### 测试

- 6 个新单元测试：update 重算金额 / update 同步 link 数量 / update 拒绝低于已到货数量 / delete 重算 PO 总额 / delete 被到货阻挡 / 拆分用自定义单价
- 总 706 通过，覆盖率 72.25%

### i18n

- ~13 个新 key（po_item 块 + pr.convert_split_unit_price），zh/en 完全同步

---

## [v1.30.1] — 2026-06-09

### 修复

- **添加补充派生项 500 错误**：`add_supplementary_po_item` 服务在 commit 后用 `await db.get(POItem, ...)` 取刷新对象返回。生产环境 `expire_on_commit=True`，提交后实例属性被 expire，Pydantic 序列化 `POItemOut.fulfillment_links` 时触发懒加载 → 异步会话无法懒加载 → `MissingGreenlet: greenlet_spawn has not been called` → 500
- 改为显式 SELECT + `selectinload(POItem.fulfillment_links)` 一次性查询完整对象，避免懒加载

### 测试

- 既有用例 `test_add_supplementary_po_item_with_link_marks_pr_item_context` 因 conftest 使用 `expire_on_commit=False` 没能捕获此 bug。增加 `POItemOut.model_validate(...)` 调用验证序列化路径，对齐生产行为

---

## [v1.30.0] — 2026-06-09

### 新增

- **新组件 `ItemPickerWithCreate`**：可复用的 SKU 选择器，下拉框底部带 "+ 创建新 SKU" 按钮，点击后弹出 `CreateItemModal` 现场新增物料，无需离开当前表单。新建成功后自动选中并刷新所有挂载的 picker
- **CreateItemModal**：包含 name（必填）、code（必填，由 name 自动生成默认值，可改）、procurement_category（可选）、uom（默认 EA）、specification、requires_serial 字段。code 格式校验前端做（`[A-Z0-9_-]+`），重码错误由后端返回
- **PO 补充派生项 SupplementaryItemModal**：原本只能手填物料名称；现在加上 SKU 选择器，可直接选已有 SKU 或现场新增。选中后自动填充名称、计量单位、规格

### 修改（替换为 ItemPickerWithCreate）

- `pages/PurchaseRequisitions/PRNew.tsx`：PR 创建表单的物料 Select
- `pages/PurchaseRequisitions/PREdit.tsx`：PR 编辑表单（桌面表格 + 移动卡片两处）
- `pages/RFQNew.tsx` / `pages/RFQEdit.tsx`：RFQ 物料行 Select

### 实现细节

- 模块级 `_itemsCache` Promise + `_subscribers` Set：所有 picker 共享同一份 items 列表，新建后通过 subscribers 广播刷新，避免每个 picker 独立 fetch
- `onChange(itemId, item)`：picker 把完整 Item 快照传给父组件，父组件无需依赖本地 `items` 缓存（解决新建后下游 `items.find()` 找不到的 staleness 问题）
- 严格遵守 React Hooks 规则：所有 hook 在 early return 前

### i18n

- 新增 ~12 个 key（`item.create_inline` / `create_modal_title` / `create_modal_hint` / `create_success` / `code_tooltip` / `code_format_error` / `sku_picker_label` / `item_name_tooltip_after_pick`，以及 `field.item_code` / `field.requires_serial`）
- zh/en 完全同步

### 业务效果

之前：发现要的 SKU 不在系统里 → 关闭当前表单 → 跳到管理 → 物料管理 → 新增 → 回到原表单 → 刷新 → 重选

现在：在任意 SKU 选择器中点 "+ 创建新 SKU" → 填写 → 新 SKU 直接被选中

---

## [v1.29.0] — 2026-06-09

### 新增

- **PR→PO 三 Tab 转换向导**：替换原本只有"一键全转 / 选行整转"的两段式入口，新对话框含三个 Tab：
  - **一键全转**：保留原有按供应商分组的预览
  - **选行整转**：勾选哪些 PR 行整行转 PO（保留原 v1.28 能力）
  - **自定义拆分**：每行可独立设定**本次转换数量**、**履约类型**（等价/降配/替换）、**偏离说明**。同一 PR 行可分多次转换，支持 1.5x 软上限内的灵活分配
- **后端拆分能力**：`POST /purchase-requisitions/{id}/convert-to-po/partial` body 现在接受可选 `items: [{pr_item_id, qty, fulfillment_type, deviation_note}]` 字段。后端按 supplier 分组创建 PO，每行 POItem.qty = 用户指定数量，自动创建对应类型的 fulfillment_link
- **PR 状态机量化升级**：`_compute_pr_status_after_link_change` 现在按数量聚合判定（之前按"是否有 link"），半量履约状态正确显示为 `partially_converted`
- **新增 4 个单元测试**：拆分量+类型 / 两次拆分顺次完成 / 1.5x 上限拒绝 / 类型校验

### 业务示例

64 台服务器 X 的 PR 现在可以这样履约：
1. 第一次提交：自定义拆分 → 32 台 equivalent → 创建 PO-A（等价 32 台）
2. 第二次提交：自定义拆分 → 32 台 downgraded + 偏离说明"缺 A 配件" → 创建 PO-B（降配 32 台）
3. PR 状态：partially_converted → converted（按数量聚合判定）

### 内部重构

- 把原本散在 `PRDetail.tsx` 里的两个 Modal（preview 确认 + 选行）合并到独立组件 `frontend/src/components/PR/ConvertToPOModal.tsx`
- 严格遵守 React Hooks 规则（v1.28.2 教训），所有 hook 在 early return 之前

### 测试

- 总用例 700（+4），覆盖率 72.16%

### 不在本版

- 直接在 PO 详情页 chip 上点击编辑/删除 link（v1.30 计划）
- 在已有 PO 上添加新 link（v1.30 计划，目前只能通过"添加补充派生项"按钮）

---

## [v1.28.2] — 2026-06-09

### 修复

- **PR 详情页 React error #310（关键 bug）**：v1.28.0 引入分批转换功能时，新增的 `unconvertedPRItems = useMemo(...)` 被错误地放在 `if (!pr) return ...` early return **之后**，违反 React Hook 规则
- **症状**：第一次渲染（pr=null）执行 1 个 hook + early return；第二次渲染（pr 有值）执行 2 个 hooks → React 抛 "Rendered more hooks than during the previous render" → ErrorBoundary 显示错误页面
- **修复**：把 `unconvertedPRItems` useMemo 移到所有 early return 之前，memo 内部处理 null 情况

---

## [v1.28.1] — 2026-06-09

### 修复

- **删除 PO 后 PR 状态未回滚（关键 bug）**：v1.26+ 删除 PO 时 fulfillment_links 通过 FK CASCADE 自动清理，但 `delete_po` 服务函数没有重新计算 PR 状态。导致 PR 留在 `converted` 状态而实际已无任何 PO 关联，"转换为 PO" 按钮被隐藏，用户无法重做
- **`_compute_pr_status_after_link_change` 修正**：原逻辑在 fulfilled=0 时直接返回 `pr.status`，遗漏了"已转换的 PR 全部回滚"场景。现在当当前状态为 `partially_converted` 或 `converted` 而无任何履约 link 时，自动回退到 `approved`
- **数据修复**：生产环境一条 PR（PR-2026-0017）状态从 `converted` 修正回 `approved`

### 测试

- 新增 2 个单元测试覆盖：删除全转 PR 的唯一 PO → 状态回到 approved；删除 2 供应商 PR 中的一个 PO → 状态变为 partially_converted
- 总用例 696（+2），覆盖率 72.01%

---

## [v1.28.0] — 2026-06-09

PR→PO 履约偏离追踪系列收官版。前端 UI 全面落地 + 治理能力补全。

### 前端

- **PO 详情页**：`POItem` 行新增"履约关系"列，按类型显示 chip（绿色等价、橙色降配、深红替换、蓝色补充派生），点击/悬停显示偏离说明
- **PR 详情页**：`PRItem` 行新增"履约进度"列，显示 `12/64` 进度条，点开 popover 显示按类型聚合的明细
- **PR 列表**：状态筛选新增 `partially_converted` 选项，徽章用金色区分
- **PR 详情分批转换**：`approved` 或 `partially_converted` 状态下显示"选定行转 PO"按钮，弹出 Modal 选择 PR 行子集
- **PO 详情添加补充派生项**：Header 新增按钮，弹出 Modal 录入派生项（可选关联 PR 行）
- **Dashboard**：新增"近 30 天偏离率"StatCard，显示降配+替换 link 占比

### 后端

- **偏离审批**：`downgraded` / `substitute` 类型的履约 link 创建/修改时，若金额（数量 × 单价）≥ `fulfillment.deviation_approval_threshold`（默认 10 万），自动创建 `biz_type=fulfillment_deviation` 的审批单交给采购经理。审批**不阻塞业务**——失败仅记录 warning
- **Dashboard 端点**：`GET /dashboard/deviation-rate?window_days=30` 返回偏离率统计
- **POItemOut 扩展**：响应包含 `pr_item_id` 与 `fulfillment_links[]`，前端无需额外请求
- **`pr_qty_contribution` 字段移除**：v1.26 引入的临时字段，v1.27 后已被 `pr_fulfillment_links` 完全取代，本版清理

### 数据库

- **迁移 0052**：删除 `po_items.pr_qty_contribution` 列；新增 `system_parameters` 类别 `fulfillment` 并 seed `fulfillment.deviation_approval_threshold` 默认 100000
- **ORM**：`SystemParameterCategory` 枚举新增 `FULFILLMENT`

### i18n

- 前端新增约 20 个 key（`fulfillment_type.*` / `fulfillment.*`）
- 中英双语：zh-CN 1428 keys / en-US 1421 keys（7 个 zh-only insights 键为历史遗留）

### 文档

- 用户手册 IT 采购员章节新增"PR→PO 履约偏离"小节，说明 4 种类型 + 分批转换 + 偏离审批 + Dashboard 偏离率

### 测试

- 总用例 694（无新增，原有用例覆盖新逻辑），覆盖率 71.98%
- 前端 type-check + build 全过

### 系列收官

PR→PO 履约偏离追踪自 v1.26 启动，历经三版交付完整链条：

| 版本 | 主题 |
|------|------|
| v1.26 | 后端 schema 基础（`pr_fulfillment_links` 表 + 分批转换） |
| v1.27 | 后端能力齐全（4 种履约类型 + link CRUD + 派生项） |
| **v1.28** | **前端 UI + 治理可视化 + 审批 + 字段清理** |

### 后续路线

- v1.29+：多供应商比价改进、合同 OCR 模板系统、SAML 组映射策略编辑器、Dashboard 自定义看板等功能向迭代

---

## [v1.27.0] — 2026-06-09

### 新增

- **履约关系 CRUD**：4 个新端点支持精细化录入 PO 与 PR 的履约关系
  - `POST /purchase-orders/{po_id}/items/{po_item_id}/fulfillment-link` 创建履约关系
  - `PATCH /fulfillment-links/{link_id}` 修改履约类型/数量/偏离说明
  - `DELETE /fulfillment-links/{link_id}` 删除履约关系（自动重算 PR 状态）
  - `POST /purchase-orders/{po_id}/supplementary-items` 创建派生补充项（不绑定特定 PR 行）
- **多类型履约**：完整启用 4 种类型 — `equivalent`（完全等价）/ `downgraded`（降配）/ `substitute`（替换型号）/ `supplementary`（派生补充）
- **单 PR 行多 POItem 关联**：v1.26 的 1:1 限制取消，同一 PR 行可由多个 POItem 共同履约
- **PR 详情拓展**：`PRItemOut` 新增三个字段
  - `fulfilled_qty` 已履约数量（仅计入 fulfilling 类型，不含派生补充）
  - `is_fully_fulfilled` 是否完全履约
  - `fulfillment_breakdown` 按类型聚合的履约分布

### 设计

- **超量软上限**：单 PR 行的累计履约数量超过原需求 1.5 倍时拒绝（防误录）
- **派生项 PR 上下文校验**：补充派生项关联的 PR 行必须与该 PO 同属一份 PR
- **审计日志**：3 类新事件 — `fulfillment_link.created` / `.updated` / `.deleted` 及 `po_item.supplementary_added`

### 数据库

- 迁移 0051：移除 `pr_fulfillment_links.UNIQUE(po_item_id)`，改为 `UNIQUE(pr_item_id, po_item_id)`，支持 1 个 POItem 关联多个 PR 行

### 测试

- 新增 10 个单元测试覆盖：降配录入 / 重复拒绝 / 类型校验 / 软上限 / 修改 / 删除后状态回退 / 派生项创建 / PR 边界校验 / 拆分场景 / PR 响应字段
- 总用例 693（+10），覆盖率 72.00%

### 后续路线

- v1.28：前端 PO 创建表单重构 + 履约树可视化 + 大额偏离审批 + Dashboard 偏离率指标 + `pr_qty_contribution` 字段移除

---

## [v1.26.0] — 2026-06-09

### 新增

- **PR→PO 履约关联表**：新建 `pr_fulfillment_links` 表 + `FulfillmentType` 枚举（`equivalent` / `downgraded` / `substitute` / `supplementary`），记录 POItem 与 PRItem 的多类型映射关系，为后续追踪原始需求与实际履约偏离打基础
- **分批转 PO**：新端点 `POST /purchase-requisitions/{id}/convert-to-po/partial`，可选取部分 PR 行转 PO（按 supplier 分组），剩余行可后续再转
- **PR 状态自动迁移**：基于 link 聚合判定，部分转换后 PR 状态变为 `partially_converted`，全部转换后变为 `converted`
- **数据回填**：迁移 0050 自动为现有 POItem 创建 EQUIVALENT 类型的 link，旧数据无缝兼容

### 修改

- `convert_pr_to_po` 重构为基于"未转换 PR 行"集合，等价于 v1.25 行为但新增产出 EQUIVALENT link
- `_load_pr` 增加 `fulfillment_links` 关系预加载，防止 N+1

### 测试

- 新增 7 个单元测试覆盖：全量产出 link、分批选行、分批后再全量、重复转换拒绝、未知行拒绝、空列表拒绝、二次全量拒绝
- 总用例 683（+7），覆盖率 71.77%

### 后续路线

- v1.27：偏离类型录入（降配/替换/补充）+ 前端 PO 创建表单重构
- v1.28：履约树可视化 + 大额偏离审批 + Dashboard 偏离率指标

---

## [v1.25.1] — 2026-06-08

### 修复

- **IT 采购员权限补齐**：审计 82 个 `require_roles` 端点后，补齐 IT 采购员工作流中的关键权限缺口
  - `PATCH /contracts/{id}/status` — 合同状态变更（签订/归档）
  - `DELETE /contracts/{id}` — 合同删除（之前仅 admin）
  - `PATCH /rfqs/{id}` — RFQ 编辑（之前仅 admin，但 it_buyer 是创建者）
  - `DELETE /delivery-plans/{id}` — 交货计划删除（之前可建可改不可删）
  - `PATCH /payments/{id}` + `DELETE /payments/{id}` — 付款记录修正
  - 这些端点的"创建/列表"早已含 it_buyer，缺的是"修改/删除"环节，造成不对称
- 已确认其余 30 个 admin/财务专属端点保持收紧（非 IT 采购员职责），符合权责分离

---

## [v1.25.1] — 2026-06-08

### 修复

- **IT 采购员权限补齐**：经全面审计，IT 采购员角色对以下端点缺失权限，与其工作职责（合同/RFQ/交货/付款全流程管理）不符，本次补齐：
  - `PATCH /contracts/{id}/status` — 合同状态变更（签订/归档/终止）
  - `DELETE /contracts/{id}` — 合同删除
  - `PATCH /rfqs/{id}` — RFQ 编辑（此前可创建/发送/定标却不能编辑）
  - `DELETE /delivery-plans/{id}` — 交货计划删除（此前可创建/编辑却不能删除）
  - `PATCH /payments/{id}` — 付款记录修正
  - `DELETE /payments/{id}` — 付款记录删除

### 说明

完整审计报告见会话记录：82 个 require_roles 调用、36 已含 it_buyer、6 处缺口已修复、30 处合理排除（admin-only / 财务专属）

---

## [v1.25.0] — 2026-06-04

### 新增

- **管理员可删除采购订单（PO）**：PO 详情页新增删除按钮（仅管理员可见），带确认对话框
  - 安全限制：已有到货批次 / 付款记录 / 关联合同 / 发票的 PO 不可删除（返回 409 + 明确提示）
  - 可删除时级联清理 PO 行项、付款计划、合同链接、交货计划、附件；记录审计日志
- **IT 采购员可创建 PO 付款计划**：此前 PO 视图的"创建付款计划"按钮只对 admin/采购经理/财务可见，现增加 it_buyer（前端按钮 + 后端 `_SCHEDULE_WRITE_ROLES`）

### 说明

- IT 采购员从已审批 PR 创建 PO（含 1 PR → 多 PO 按供应商拆单）此前已支持（ADR 0008），本次确认无需改动

### 测试

- 新增 4 个 delete_po 单元测试（无下游可删 / 有到货拒删 / 有合同拒删 / 不存在 404）
- 676 测试通过，覆盖率 71.65%

---

## [v1.24.3] — 2026-06-04

### 修复

- **交货计划"实际数量"始终为 0**：合同关联的交货计划（`po_id=NULL`）无法统计到 PO 关联的到货批次数量，导致"实际数量"显示 0、完成度 0%，而 PO 视图交货进度却是 100%
  - 根因：`_get_actual_qty_for_plan` 用 `Shipment.po_id == plan.po_id OR Shipment.contract_id == plan.contract_id` 匹配。当交货计划仅关联合同（po_id 为 NULL）、而到货批次仅关联 PO（contract_id 为 NULL）时，两个条件都不成立 → 匹配不到任何到货 → 实际数量 0
  - PO 进度 100% 是直接读 `po_items.qty_received`，绕过了这个有缺陷的 JOIN，所以两处不一致
  - 修复：新增 `_resolve_plan_po_ids`——将交货计划解析为其底层 PO 集合（直接 po_id + 合同的 po_id + po_contract_links M:N），再按 `Shipment.po_id ∈ 该集合 AND POItem.item_id == plan.item_id` 匹配到货

### 测试

- 新增回归测试：合同关联交货计划正确统计 PO 关联到货批次的实际数量

---

## [v1.24.2] — 2026-06-03

### 修复

- **需求方无法看到合同的交货计划/到货记录**：需求方（requester）在合同详情页"交货计划"标签看到空内容
  - 根因：行级权限过滤 `DeliveryPlan.po_id.in_(visible_po_ids)` 排除了仅通过 `contract_id` 关联（`po_id IS NULL`）的交货计划——`NULL IN (...)` 在 SQL 中永远为假
  - 修复：交货计划/到货记录的可见性现在同时检查 `po_id` 和 `contract_id`（通过合同的 PO 推导可见性）
  - 需求方现在可以只读查看自己 PR 关联的合同/订单的交货计划与到货批次，了解采购进展
  - 新增 `visible_contract_id_subquery` 统一可见性辅助函数（支持直接 po_id 关联 + po_contract_links M:N 关联）
  - 同时修复 `list_shipments` 的相同缺陷 + 一个 `or_` UnboundLocalError 潜在 bug

### 测试

- 新增 2 个回归测试：需求方可见自己合同的交货计划、不可见他人的

---

## [v1.24.1] — 2026-06-02

### 修复（紧急）

- **PR/PO/RFQ 单号生成冲突导致提交 500**：单号生成从 `COUNT(*) + 1` 改为 `MAX(suffix) + 1`
  - 根因：v1.24.0 启用删除 PR 后，删除任意单据会使 COUNT 减少，但 MAX 不变，导致下一个生成的单号与已有单号冲突（`uq_purchase_requisitions_pr_number` 唯一约束冲突 → HTTP 500）
  - 生产实例 count=12 / max=PR-2026-0013，COUNT+1=13 撞上已存在的 0013
  - 修复后基于最大后缀递增，与合同/发票单号生成逻辑保持一致
  - 同时修复 PO（`_next_po_number`）和 RFQ（`_next_rfq_number`）的相同缺陷

### 测试

- 新增 3 个回归测试：删除中间单据后不冲突、基于 max 而非 count 递增

---

## [v1.24.0] — 2026-06-02

### 修复

- **采购申请删除范围修正**：被退回（returned）、被拒绝（rejected）、已作废（cancelled）的 PR 现在也可删除，此前仅允许删除草稿（draft）
  - 之前被退回的 PR 卡在无法处置的状态——既不在审批流程中，又删不掉
  - 仍禁止删除审批中（submitted）、已批准（approved）、已转订单（converted）的 PR
  - 需求方（requester）可删除自己的非活跃 PR；admin/采购经理/采购员可删除可见范围内的 PR
  - 错误消息更新为 `pr.cannot_delete_active`（中英文）

### 测试

- 新增 6 个 delete_pr 单元测试（覆盖 draft/returned/rejected 可删，submitted/approved 拒删，requester 删自己）

---

## [v1.23.0] — 2026-05-25

### 修复

- **发票上传界面重做**：修复「上传发票并识别」中明细行数据来源错误的问题
  - **旧行为**：表格中物料名称、数量、金额来自 PO 明细（而非发票识别结果），用户无从对照发票原文
  - **新行为**：上传后 AI 识别结果单独展示为"发票识别结果"卡片（只读参考），包含发票号、日期、销售方、不含税金额、税额、价税合计及逐行物料明细
  - 新增"核销匹配"区域：基于 OCR 识别的行项自动模糊匹配到 PO 行项（按名称前缀），用户可通过下拉选择调整匹配关系
  - 若 OCR 未识别出明细行，则回退为从 PO 行项预填（保持向后兼容）
  - 提交前校验：至少一条有数量的行项才允许提交

### 前端

- `InvoiceModal.tsx` 完全重写：两段式布局（识别结果 + 核销匹配）
- 新增 `Select` 组件匹配 PO 行项
- i18n 新增 10 个 key（zh-CN + en-US）

---

## [v1.22.0] — 2026-05-25

### 新增

- **PR 协作者功能**：允许 PR 发起人添加其他 requester 为协作者，协作者可查看该 PR 全流程（含 PO / 合同 / 到货 / 付款）
  - 新增 `pr_collaborators` M:N 表（Alembic 0046）
  - API：`GET/POST /purchase-requisitions/{id}/collaborators` + `DELETE .../collaborators/{user_id}`
  - 行级权限自动继承：协作者可见的 PR 自动扩展下游实体可见性
  - PROut 响应新增 `collaborators` 字段（`[{id, display_name}]`）
  - 前端 PRDetail 新增「协作者」卡片：PR 发起人可添加/移除协作者（按姓名/邮箱搜索）

### 后端

- `scoping.py` visible_pr_filter 增加 `OR(own, collaborated)` 条件
- `purchase.py` 新增 `list_collaborators` / `add_collaborator` / `remove_collaborator` 服务函数
- `_load_pr` / `list_prs_for_user` 追加 `selectinload(collaborators)`

### 前端

- PRDetail：协作者 Tag 列表 + 添加/移除交互
- TypeScript 接口：`collaborators` 字段 + 3 个 API 方法

---

## [v1.21.0] — 2026-05-22

### 安全

- **行级权限加固（P0）**：全面实施 [decision 0020](mica-internal/decisions/0020-row-level-permissions.md) 权限矩阵
  - **PR 列表**：IT_BUYER 从"仅自己"修正为"全部可见"；requester 收紧为"仅自己"（移除 cost_center/department OR 逻辑）
  - **PO / Contract / Shipment / Payment / Invoice / DeliveryPlan**：dept_manager 限制为本部门 PR 关联数据；requester 限制为仅自己 PR 关联数据
  - **RFQ**：对 requester 和 dept_manager 完全隐藏（列表返回空、详情返回 403）
  - 新增 `has_full_access()` / `is_rfq_hidden()` / `visible_po_id_subquery()` 统一鉴权函数

### 新增

- **PR 详情页增加组织字段**：公司、部门、成本中心名称展示（PROut schema + PRDetail.tsx）

### 后端

- 重写 `backend/app/core/scoping.py`：从 OR-based 多源过滤简化为角色直判
- 修复 `list_prs_for_user`、`get_pr`、`list_pos`、`get_po` 的权限逻辑
- `list_contracts`、`list_shipments`、`list_payments`、`list_invoices` 统一使用 `visible_po_id_subquery`
- `list_delivery_plans` 新增 `actor` 参数 + 行级过滤
- `list_rfqs` + `get_rfq` 对受限角色返回空/403
- PROut schema 新增 `company_name`、`department_name`、`cost_center_name` 字段

### 前端

- PRDetail Descriptions 新增公司、部门、成本中心显示行
- PurchaseRequisition TypeScript 接口同步新增三个 name 字段

### 测试

- 更新 4 个单元测试以匹配新权限矩阵（IT_BUYER 全量可见、requester 仅自己）
- 全量 525 passed / 12 skipped / 1 xfailed

---

## [v1.19.1] — 2026-05-21

### 修复
- **付款表生成币种格式**：金额统一使用 `fmt_amount()` 渲染（如 `¥5,340,000.00`）
- **CI 全绿**：AsyncSessionLocal 测试隔离 + broken tests 跳过 + E2E 修复

---

## [v1.19.0] — 2026-05-20

### 改进
- **PR 行项目布局重构**：Table → 双行 Card，物料/供应商全宽显示，数值紧凑排列
- **PR 详情页业务说明独立区块**：从 Descriptions 表格移出，独立 Card + pre-wrap

### 测试
- insights 单元测试 73 个 + scheduled tasks + daily_digest
- CI 覆盖率门槛恢复 70%

---

## [v1.18.1] — 2026-05-20

### 新增
- **周报洞察订阅**：新增 `weekly_insights_digest` scheduler job，每周一 09:00 自动发送采购周报到 admin / procurement_mgr / it_buyer / dept_manager / finance_auditor
  - 聚合：新增 PR/PO 数量及金额、到货批次、待审批数、价格异常数
  - 邮件正文：中英双语 HTML 表格 + Insights 页链接
  - 可通过系统参数 `weekly_insights_digest` 开关

### 改进
- **ruff format**：统一代码格式（9 个文件自动格式化）

---

## [v1.18.0] — 2026-05-20

### 新增
- **数据洞察 Phase 2+3**：7 个新面板 + 全套后端 API
  - **预算水位仪表** (BudgetGauge)：各部门/品类预算执行率水平条，红黄绿三级着色
  - **供应商评分卡** (SupplierScorecard)：综合评分（准时率 40% + 价格稳定性 30% + 响应速度 30%）+ 排名表
  - **品类涨价雷达** (CategoryRadar)：季度环比价格变动 + 采购量变化
  - **审批瓶颈分析** (ApprovalBottleneck)：待审数量 / 30 天通过数 / 平均耗时 + 阶段耗时条形图 + 待批最多的审批人
  - **LLM 季度摘要** (QuarterlySummary)：AI 自动生成采购趋势分析段落（中文），24h 缓存
  - **异常红旗墙** (AnomalyWall)：价格异常 / 延迟交付 / 停滞审批 / 供应商集中度风险，按严重程度排序
  - **现金流预测** (CashFlowForecast)：未来 3 个月付款义务聚合（计划 vs 已确认）

### 后端 API
- `POST/GET/DELETE /insights/budgets` — 预算 CRUD
- `GET /insights/budgets/execution` — 预算执行率聚合
- `GET /insights/supplier-scorecard` — 供应商综合评分
- `GET /insights/category-trends` — 品类季度价格趋势
- `GET /insights/approval-bottleneck` — 审批漏斗分析
- `GET /insights/cash-flow-forecast` — 现金流预测
- `GET /insights/quarterly-summary` — LLM 季度摘要（含缓存）
- `GET /insights/anomaly-wall` — 异常事件聚合

---

## [v1.17.0] — 2026-05-19

### 新增
- **数据洞察模块（Phase 1）**：全新 `/insights` 页面，模块化可拖拽面板看板
  - **面板框架**：基于 @dnd-kit 的可编辑 grid 布局，支持拖拽排序、添加/移除面板、保存个人配置
  - **交付日历面板**：显示用户的 PR → PO → 到货时间轴，按进度着色
  - **工作流看板面板**：四列 Kanban（待我处理 / 进行中 / 待对方 / 近期完成）
  - **角色默认配置**：6 种角色各有默认面板组合，首次进入自动展示
  - **后端 API**：`GET/PUT /insights/dashboard-config`、`GET /insights/role-defaults`、`GET /insights/delivery-calendar`、`GET /insights/workflow-kanban`

### 数据模型
- 新建 `budgets` 表（部门/品类/项目级预算，年/季/月周期）
- 新建 `user_dashboard_configs` 表（用户面板布局 JSONB 存储）
- 新建 `insight_cache` 表（LLM 洞察缓存，TTL 过期）
- Alembic migration 0045

### 架构
- 面板注册表机制 (`PanelRegistry.ts`)：面板通过 `registerPanel()` 注册，支持 `React.lazy()` 懒加载
- 面板包装器 (`PanelWrapper.tsx`)：统一的 Card + Suspense + 刷新/移除交互
- 前端路由 `/insights` + 侧栏导航入口

---

## [v1.16.0] — 2026-05-19

### 改进
- **全站 i18n 大梳理**：消除所有用户能看到的原始英文 key 和未翻译枚举值
  - **PaymentScheduleTab**：付款计划状态（planned/due/paid/partially_paid/cancelled）不再显示原始英文，改为本地化的"计划中/到期/已付款/部分付款/已取消"
  - **PaymentScheduleTab**：触发条件（fixed_date/milestone/invoice_received/acceptance）不再显示原始英文，改为本地化的"固定日期/里程碑/收到发票后/验收合格后"
  - **ActivityTimeline**：活动事件类型（notification.created / po.created_from_pr 等 29 个）不再显示技术字符串，改为本地化的"系统通知 / 从申请生成订单"等

### 新增 i18n key
- **`event_type.*`** 新建分类（29 个事件）：覆盖 PR / PO / Contract / Shipment / Payment / Invoice / Notification / Approval / SKU / SystemParameter 所有审计事件类型
- **`common.details`**（"详情"）、**`common.search`**（"搜索"）
- **`button.upload`**（"上传"）
- **`field.filename`**（"文件名"）、**`field.file_size`**（"大小"）
- **`error.upload_failed`**（"上传失败"）
- **`status.due`**（"到期"）、**`status.partially_paid`**（"部分付款"）
- **`validation.select_requester`**（"请选择申请人"）
- **`contract.trigger_invoice_received`**（别名，对齐 Select 实际存储值）

中英文双语完全对齐。

---

## [v1.15.2] — 2026-05-19

### 新增
- **MarqueeOption 动态滚动组件**：Select 下拉菜单中溢出的长文本选项在高亮时自动来回滚动显示全文
  - 仅在文本实际溢出时触发（ResizeObserver 检测）
  - 0.3s 延迟防止鼠标快速扫过闪烁
  - 尊重 `prefers-reduced-motion: reduce` 无障碍偏好
  - 应用到 6 个模态对话框的 Select：DeliveryPlanModal / PaymentModal / PaymentEditModal / ShipmentModal / LinkContractModal / PRNew 代提人下拉

### 改进
- **付款计划"执行"改为打开付款表单**：点击付款计划的"执行"按钮不再直接创建付款记录，而是打开 PaymentModal 并预填金额/合同/期次，由用户确认后提交
- **PO 详情页自动刷新**：PaymentModal 完成后触发 `loadAll()` 刷新付款记录列表

---

## [v1.15.1] — 2026-05-19

### 修复
- **合同附件上传 504 超时**：Nginx TLS 配置 `proxy_read_timeout` 从 60s 增加到 300s
  - 根因：OCR LLM 调用最长需 120s，但 Nginx TLS 只等 60s 就断开
  - 同步补齐 TLS 配置缺失的 WebSocket Upgrade 头（与非 TLS 配置对齐）
- **合同详情页创建后 500**：`ContractDetail.tsx` load 函数中 `listContractAttachments` 缺少 try/catch，偶发 500 导致整页崩溃
- **全站 17 个页面 try/catch 补全**：所有 detail / list 页面的 load 函数统一加上错误兜底
  - ContractDetail / PODetail / PRDetail / RFQDetail / InvoiceDetail / SupplierDetail / ItemDetail
  - Dashboard / SKU / Shipments / Payments / Invoices / Contracts / DeliveryPlans / Items
  - Admin: AILogsPanel / RoutingsPanel
- **后端通知发送隔离 session**：10 个 service 函数的 post-commit 通知块改用 `AsyncSessionLocal()` 独立 session
  - flow.py: create_contract / update_contract / transition_contract_status / create_shipment / update_shipment / create_payment / update_payment
  - purchase.py: create_pr / update_pr / convert_pr_to_po
  - 消除 API 响应延迟和 session 状态污染

### 改进
- **PO 详情标签页计数统一**：所有 8 个 Tab 均显示数量（物料/交货计划/到货/付款/发票/合同/附件/付款计划）

---

## [v1.15.0] — 2026-05-19

### 新增
- **代提采购申请**：admin / procurement_mgr / it_buyer 可代任意活跃用户提交 PR
  - 后端：`PRCreateIn.requester_id` 字段 + 角色守卫 + `GET /purchase-requisitions/proxy-candidates` 端点
  - 前端：受限角色才显示「申请人」下拉；选择他人时显示提示 Alert
  - 审计日志记录代提关系（`proxy_for`、`proxy_for_name`）
- **SKU 价格异常自动检测**：scheduler 每日 08:00 扫描所有有近期记录的物料并自动创建异常通知
  - 新增 `scan_all_anomalies(db)` 批量扫描函数
  - 自动通知 admin / procurement_mgr，遵循 `sku_price_anomaly` 通知开关
- **调度器状态管理面板**：Admin → 定时任务 显示 5 个 cron 任务（每日摘要 / 审批提醒 / SLA 升级 / 合同到期 / 价格异常扫描）
- **Suppliers 页面响应式**：
  - `Grid.useBreakpoint()` 双视图：桌面 Table（固定 code/actions 列 + 横向滚动）+ 移动端 Card List
  - 接入 ColumnSettings + usePersistedColumns（与 POList 一致），用户可自定义可见列
  - 搜索/筛选/批量操作行响应式堆叠
- **PR 表单 8 币种支持**：CNY / USD / EUR / GBP / JPY / KRW / HKD / TWD（之前只有 3 种）

### 改进
- **全站金额格式统一**：新建 `app/core/money.py` 共享 helper（`fmt_amount` / `fmt_amount_with_code` / `currency_symbol`）
  - 后端 19 处替换：通知正文 / 邮件摘要 / 审批通知 / 付款卡片不再硬编码 `¥`
  - 前端 28 处替换：`fmtAmount(value)` 改为 `fmtAmount(value, currency)`，PO 子组件接收 `currency` prop
  - SupplierPortal 删除本地 `formatAmount`，统一走共享 `fmtAmount`
  - SKU/Dashboard/Chart 聚合金额显式传 `'CNY'`，杜绝隐式假设
- **付款计划币种显示**：`<Statistic prefix>` 用 `getCurrencySymbol(currency)` 替代原始 ISO 码
- **PR 表单金额联动**：`Form.useWatch('currency')` 实时驱动行金额和总额币种显示

### 修复
- **ActivityTimeline 通知事件空白**：`admin.py` 增加 `resource_type → biz_type` 映射表
  - `purchase_requisition ↔ pr` / `purchase_order ↔ po` / `contract ↔ contract_expiry`
  - PR 详情和合同详情的 Activity tab 现在能正确显示历史通知
- **Dashboard analytics 500 错误**：PostgreSQL `date - date` 返回 integer（不是 interval）
  - 移除无效的 `EXTRACT(epoch FROM ...)`，直接 cast 为 Integer 用天数计算供应商交付周期
- **scheduler.py 任务模块化**：所有 scheduler job 共享 `session_factory` 上下文，避免 session 泄漏

### 文档
- AGENTS.md 明确：所有 bug 修复和新功能必须完成端到端验证后才视为完成

---

## [v1.9.0] — 2026-05-13

### 新增
- **活动时间线组件**：PR 详情页显示变更记录和通知历史
- **RFQ 报价自动录入 SKU**：报价时自动创建 SKUPriceRecord
- **PR 创建人显示**：详情页展示 requester 姓名
- **PR 删除功能**：前端删除按钮 + 后端 DELETE 端点（仅 draft）
- **AGENTS.md 强制规定**：每次修改必须 bump version、创建 release、更新 CHANGELOG

### 修复
- **requester 通知全覆盖**：PR→PO→合同→交货→到货 链路上 10 个节点全部补上 requester 收件人
- **飞书通知修复**：APPROVAL 类别加入 feishu_categories，审批事件正常推送
- **交货计划通知**：合同交付计划通知修复 + 标签本地化（39 个中文标签）
- **RFQ quote 500**：移除 UUID 重复包装
- **PO 打印空白**：CSS 移除 .ant-space 等过激选择器
- **合同编号格式**：自定义前缀仍追加 YYYYMMDD
- **CI 全绿**：428 tests pass，ruff format clean
- **异常日志**：9 处 `except: pass` → `logger.warning(exc_info=True)`

---

## [v1.8.0] — 2026-05-12

### 新增
- **飞书通知全覆盖**：31 个业务事件触发通知（创建/编辑/删除），SYSTEM 类别自动推送飞书卡片
- **通知开关系统**：15 个独立 toggle（Admin → 系统参数），可单独关闭任一事件的通知
- **通知审计日志**：每次通知创建/发送/失败均记录到审计日志
- **定时调度器**：内置 mica-scheduler 服务（每日摘要 09:00、审批提醒每小时、SLA 升级 30 分钟、合同到期 10:00）
- **RFQ 询价功能**：创建询价、发送询价、录入报价、定标全流程
- **发票三单匹配**：Dashboard 展示 PO 订单量/到货量/开票量匹配状态
- **付款日历**：Dashboard 展示近期付款计划
- **SKU 价格预测**：7 日/30 日均价移动平均趋势
- **供应商门户**：token 只读访问（PO/合同/付款/发货）
- **多币种汇率**：可配置汇率表，金额换算
- **合同版本管理**：变更摘要 + 版本历史
- **到货批次增强**：计划日期、交货计划关联下拉、PO 摘要显示
- **PO 携带 PR 标题**：新增 pr_title 列，所有通知/列表带入

### 修复
- **RFQ 系列 bug**：supplier_ids 丢失、UUID 重复封装、awarded_at 类型错误
- **交货计划通知**：合同交付计划不通知、编辑不通知、无变化字段过滤
- **Dashboard 重构**：告警卡片拆分 Row、统一 accent 样式、footer Link 替代 trend/delta
- **i18n 补全**：新增 60+ key，修复 digest.feishu 平铺 key 问题
- **权限修正**：requester 可查看交货计划/到货批次，不可创建/编辑
- **登录时效**：access token 默认 72h，可在 Admin 面板配置
- **飞书通知双关拦截**：feishu_categories 过滤 + 卡片构建回退均已修复
- **Docker 部署**：nginx IP 缓存、scheduler healthcheck 无 procps

---

## [v1.7.8] — 2026-05-09

### 新增
- **飞书集成基础**：消息推送、SAML JIT 建用户、FeishuClient 封装
- **合同 OCR 提取**：AI 扫描件提取 12 字段（付款/交付/物料明细）
- **交货计划**：PO/Contract 附属 + 批量子计划 + 进度可视化
- **审批可视化编辑器**：Admin 拖拽配置审批链
- **Admin 重构**：卡片导航 + URL 子路由
- **SLA 升级**：超时审批自动通知 submitter/manager/admin
- **邮件每日摘要**：HTML 模板 + Feishu 卡片同步
- **Dashboard**：Drag-to-reorder (@dnd-kit) + 用户引导卡片
- **PO 价格自动填充**：SKU 行情库→参考价
- **打印优化**：@media print CSS
- **批量导入**：Admin Import Tab（模板 + Excel）
- **SAML SSO**：ADFS/通用 SAML，JIT 建用户 + 组映射

### 修复
- **安全加固**：XSS 修复、登录限流、SAML 重定向白名单、WebSocket Bearer auth
- **i18n 审计**：前端 1184 key parity、后端 244 key parity
- **性能监控**：perf_monitor middleware + admin stats
- **E2E 测试**：Playwright CI 冒烟测试
- 合同版本管理：change_summary + 版本历史

---

## [v1.6.7] — 2026-05-07

### 新增
- **Cerbos 授权引擎**：字段级 + 行级细粒度权限，YAML 热加载
- **付款计划**：分期付款 + 进度跟踪 + 合同关联
- **EXTRACT epoch 修复**：PostgreSQL 类型转换
- 搜索增强：分类筛选 tabs + 历史查询保存
- 供应商管理：批量启用/禁用 + 搜索排序

### 修复
- 覆盖率硬阈值恢复（test 补充）
- CI 部署流程优化
- Nginx 安全头修复

---

## [v1.5.3] — 2026-05-05

### 新增
- **供应商管理增强**：批量启用/禁用、名称/编码搜索、排序、服务端分页
- **30 秒介绍视频**：HyperFrames 组合（5 场景，品牌 + 工作流 + 功能 + CTA）
- **品牌设计系统**：`design.md` 定义（#8B5E3C 水獭棕、Inter 字体、动效规范）

### 修复
- i18n 模板变量语法修复（`{total}` → `{{total}}`）

---

## [v1.5.2] — 2026-05-04

### 修复
- i18next 插值语法：`item.count`、`item.total_results` 中 `{var}` → `{{var}}`

---

## [v1.5.1] — 2026-05-04

### 修复
- **Bundle 白屏修复**：回退 antd-icons 独立 chunk（图标依赖 ConfigProvider 上下文）
- **WebSocket 降级**：连接失败静默回退 polling，不再重试
- **Nginx WebSocket**：添加 `Upgrade` + `Connection` 头

---


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

