# Receipt Decoupling（发货与收货解耦）

## Objective

让**收货**成为独立于**发货**的动作：申请人可以在订单管理里按订单确认收货，支持部分收货与多次收货，只填数量；采购员登记交货批次表示"已发货"。订单状态随之呈现 **待发货 → 已发货 → 部分收货 → 已完成** 四态。

来源：采购同事的优化需求（2026-10-20），本轮由用户指定"按需求做完整解耦"。

## Status

**已实现，2026-10-20，待发布（目标 v1.59.0）。**
前置：v1.58.3（`ec73d32`）已修掉 200% 到货与"改不了到货数量"，本设计建立在它建立的"批次行可重算"基础上。

实现时对文末的开放问题采用了默认选择，**若与团队结论不符需要回改**：

1. 能看到该订单的 `requester` 即可收货（不限定申请人本人）；
2. 收货可随时撤销（记录人本人，或 admin / it_buyer / procurement_mgr），全部写审计；
3. 不做"实收差异"标记，只记数量；
4. **未接通知**——`receipt.created` / `receipt.deleted` 只落审计，没有给采购员发通知（与设计稿的默认相反，留作后续）；
5. 状态中文文案按需求全局替换（见下方"已知影响"）。

验证：后端 **865 passed**（含 12 个收货用例）、`ruff check app` / `ruff format --check app` 通过、迁移 `0063` 在 PostgreSQL 16 上执行通过；前端 `type-check` / `build` 通过、Vitest **96 passed**、i18n 中英 parity 干净。

### 已知影响（发布前需知会）

- 状态文案变化：`confirmed` 已确认 → **待发货**、`partially_received` 部分到货 → **部分收货**、`fully_received` 完全到货 → **已完成**，新增 `shipped` **已发货**。仪表盘、洞察、导出报表的用词会同步变化。
- 登记交货批次**不再**填写收货数量：订单随后进入"已发货"，收货由申请人在订单详情的「收货」页签完成。

## Confirmed facts（只读调研，2026-10-20）

- **现在收货与发货是同一个动作**：`create_shipment` 在登记批次时同时写 `qty_shipped` 与 `qty_received`，后者默认等于前者——`backend/app/services/flow.py`（`qty_received = _as_decimal(item_in.get("qty_received", qty_shipped))`）。采购员一次操作表达了"发货"和"收货"两件事。
- **PO 状态只由收货量推导**：`_receipt_status()`（`backend/app/services/flow.py:752-760`）只产出 `fully_received / partially_received / confirmed` 三种，且 `POStatus` 枚举里**没有"已发货"**（`backend/app/models/__init__.py:58-64`）。
- PO 创建即 `confirmed`（`backend/app/services/purchase.py:848, 998, 1565`）。
- **`ShipmentItem.qty_received` 是当前收货量的存储位置**，`recompute_po_receipt()` 从它求和（`flow.py:730-748`）。它的下游消费者很窄：批次弹窗与列表的展示（`frontend/src/components/PO/ShipmentModal.tsx:36-37,178`、`components/PO/ShipmentsTab.tsx:111`）。**导出与报表读的是 `POItem.qty_received`**（`backend/app/services/export_datasets.py:625`、`export_excel.py:664`）。
- `Shipment.received_by_id` 已存在（`models/__init__.py:852`），可作为回填收货人的来源。
- 状态文案现为 `confirmed=已确认 / partially_received=部分到货 / fully_received=完全到货`（`frontend/src/i18n/locales/zh-CN/common.json` 的 `status.*`）；`statusTag()` 是**恒等函数**（`components/PO/POHeader.tsx:21-23`），新增状态只需补 i18n 与 state class。
- **申请人的行级可见性已经具备**：`visible_po_id_subquery`（`backend/app/core/scoping.py:81-89`）使 requester 只能看到自己 PR 派生的 PO。
- ⚠️ **PO 状态被多处按值白名单过滤**，新增 `shipped` 必须逐一复核，否则新状态订单会从看板/洞察里消失：`backend/app/api/v1/dashboard.py:440-442`、`api/v1/insights.py:274-275,310-311,1085`、`services/payment_schedule.py:542-545`。

## Design decisions

### D1 · 收货记录独立成表，收货量以它为准

新增 `receipts`：

| 列 | 说明 |
| :--- | :--- |
| `id` | PK |
| `po_id` / `po_item_id` | 归属（`ON DELETE CASCADE`） |
| `shipment_id` | 可空。指向"这批货对应的批次"，`ON DELETE SET NULL`——批次被删不该抹掉收货事实 |
| `qty` | 本次收货数量，必须 > 0 |
| `received_by_id` | 谁确认的（可空，`ON DELETE SET NULL`） |
| `received_at` | 收货时间 |
| `notes` | 备注 |

**聚合链改为一条**：`Receipt.qty` → `POItem.qty_received` → `PO.qty_received` / `PO.status`。

`ShipmentItem.qty_received` **降级为派生缓存**（= 该批次下 `receipts` 之和），由 `recompute_po_receipt()` 一并写回。这样批次的展示与"这批收了多少"的直观语义都保留，而 PO 汇总不再依赖它——两个数字不会再各说各话。

### D2 · 状态机

| 条件 | 状态 | 中文文案 |
| :--- | :--- | :--- |
| 无收货、无批次 | `confirmed` | 待发货（原"已确认"） |
| 无收货、有批次 | **`shipped`（新增）** | 已发货 |
| 0 < 收货 < 订购量 | `partially_received` | 部分收货（原"部分到货"） |
| 收货 ≥ 订购量 | `fully_received` | 已完成（原"完全到货"） |
| `draft` / `cancelled` / `closed` | 原样不动 | — |

`POStatus` 加 `SHIPPED = "shipped"`。列是 `String(32)`（`models/__init__.py:570-571`）而非 PG enum，**加值不需要 DDL**。

### D3 · 权限

| 动作 | 允许角色 | 行级 |
| :--- | :--- | :--- |
| 登记收货 `POST /purchase-orders/{po_id}/receipts` | `requester`、`admin`、`it_buyer`、`procurement_mgr` | requester 限 `visible_po_id_subquery` 内的 PO |
| 查看收货记录 | 同 PO 可见性 | 复用 PO 的 `get_po` |
| 撤销收货 `DELETE /receipts/{id}` | `admin`、`it_buyer`、`procurement_mgr`，或该记录的 `received_by_id` 本人 | 同上 |

沿用 v1.58.3 定下的原则：**写端点必须有角色门 + 归属校验**，不允许"登录即可写"。
`finance_auditor` 与 `dept_manager` 不参与收货。

### D4 · 兼容与迁移（`0063_receipts`）

1. 建 `receipts` 表 + 索引（`po_id`、`po_item_id`、`shipment_id`）。
2. **回填历史收货**：把现有 `shipment_items.qty_received > 0` 的行转成 `receipts`（收货人取 `shipments.received_by_id`，缺失则取 `purchase_orders.created_by_id`；时间取 `shipments.actual_date`，缺失则 `created_at`）。回填后 PO 汇总值与迁移前一致。
3. 按 D2 重算全部 PO 状态（含新 `shipped`）。

### D5 · 本轮不做

- **拒收/差异/短装**：需求未提，`qty` 只接受正数，不做"实收 < 发货"的差异流程。
- **收货触发付款计划**：`PaymentTriggerType.ACCEPTANCE` 已存在，理论上收货后应能触发 acceptance 期次；本轮**不接线**，列为后续。
- 不动 `POItem.qty_invoiced` 与发票链；不改编批次（`ShipmentItem.qty_shipped`）语义。

## Write scope（预期）

```
backend/app/models/__init__.py            # Receipt 模型 + POStatus.SHIPPED
backend/app/schemas/__init__.py           # ReceiptIn / ReceiptOut
backend/app/services/flow.py              # recompute_po_receipt 改数据源；收货 CRUD
backend/app/api/v1/flow.py                # 3 个端点
backend/migrations/versions/0063_receipts.py
backend/app/api/v1/dashboard.py           # 状态白名单复核
backend/app/api/v1/insights.py            # 状态白名单复核
backend/app/services/payment_schedule.py  # 状态白名单复核
frontend/src/components/PO/*              # 收货入口（shipments tab 或 items tab）
frontend/src/api/index.ts                 # 收货 API 封装
frontend/src/i18n/locales/{zh-CN,en-US}/common.json
backend/tests/unit/test_flow.py           # 收货回归
```

## Acceptance criteria

1. 登记批次（不改收货量）后 PO 变 `shipped`；申请人收货后按数量变 `partially_received` / `fully_received`。
2. 同一 PO 行可分多次收货，`POItem.qty_received` 等于各次之和；删掉某次收货后汇总与状态随之回落。
3. 累计收货不得超过 订购量 × `fulfillment.over_receipt_tolerance`（v1.58.3 的容差，默认 1）。
4. `requester` 只能给自己 PR 派生的 PO 收货；对他人 PO 的收货请求返回 403，`finance_auditor` / `dept_manager` 返回 403。
5. 批次被删除时，已登记的收货记录**保留**（`shipment_id` 置空），PO 收货量不变。
6. `draft` / `cancelled` / `closed` 的 PO 拒绝收货。
7. 迁移后：所有 PO 的 `qty_received` 与迁移前一致；状态按 D2 推导。
8. 看板/洞察/付款计划的 PO 状态白名单包含 `shipped`，订单不因新状态从视图中消失。

## Open questions（需拍板）

1. **谁能收**：只有 PR 申请人本人，还是该部门/任何能看到该 PO 的人？*默认：能看到该 PO 的 requester 即可收。*
2. **撤销时限**：收货登记后是否允许随时撤销（靠审计留痕），还是超过某期限需走 admin？*默认：随时可撤，全部写审计。*
3. **是否需要"实收差异"**：例如供应商发 10 收 8 时是否要标记差异原因？*默认：不做，只记数量。*
4. **收货是否通知采购员**：*默认：发通知（复用现有通知渠道），避免采购员不知道货已到。*
5. **文案替换范围**：`partially_received` / `fully_received` 的中文从"部分到货 / 完全到货"改为"部分收货 / 已完成"会同时影响仪表盘、洞察与导出报表的用词。*默认：全局统一改。*
