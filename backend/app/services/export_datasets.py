"""Concrete export datasets.

Every dataset is a static declaration consumed by
``app/services/export_registry.py``. Row granularity follows the ledger rule:
one row per *master* record, with one-to-many data flattened into cells, and
extra detail promoted to its own sheet rather than multiplied into extra rows.

Importing this module registers the datasets.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import Select, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    Contract,
    ContractStatus,
    DeliveryPlan,
    DeliveryPlanStatus,
    Invoice,
    InvoiceLine,
    InvoiceStatus,
    Item,
    PaymentRecord,
    PaymentStatus,
    POContractLink,
    POItem,
    POStatus,
    PRItem,
    PRStatus,
    PurchaseOrder,
    PurchaseRequisition,
    Shipment,
    ShipmentStatus,
    SKUPriceAnomaly,
    SKUPriceBenchmark,
    SKUPriceRecord,
    Supplier,
    User,
)
from app.services.export_excel import _num, collect_procurement_ledger
from app.services.export_registry import (
    ExportColumn,
    ExportDataset,
    ExportFilters,
    ExportRequest,
    ExportSheetSpec,
    apply_date_range,
    keyword_clause,
    register,
)

# ---------------------------------------------------------------------------
# small formatting helpers
# ---------------------------------------------------------------------------


def _d(value: date | datetime | None) -> str:
    return value.isoformat() if value else ""


def _col(
    key: str,
    header_zh: str,
    header_en: str,
    get,
    *,
    field: str | None = None,
    width: int = 18,
) -> ExportColumn:
    return ExportColumn(
        key=key, header_zh=header_zh, header_en=header_en, get=get, field=field, width=width
    )


def _with_index(rows: list[list[Any]]) -> list[list[Any]]:
    """Stamp the 1-based row number into the leading column.

    Every loader below starts its rows with a ``0`` placeholder, so this
    *replaces* index 0 rather than inserting — inserting would shift every real
    value one column to the right.
    """
    for index, row in enumerate(rows):
        row[0] = index + 1
    return rows


# ---------------------------------------------------------------------------
# row-level scoping helpers
# ---------------------------------------------------------------------------


async def _visible_po_ids(db: AsyncSession, actor: User):
    from app.core.scoping import visible_po_id_subquery

    return await visible_po_id_subquery(db, actor)


async def _visible_po_id_set(db: AsyncSession, actor: User) -> set[UUID] | None:
    """Materialised visible PO ids, for filtering *secondary* sheets.

    The header query can rely on the subquery, but rows that hang off a
    related record (a contract link, an invoice line) must be filtered against
    an explicit set or they leak data from out-of-scope POs.
    """
    visible = await _visible_po_ids(db, actor)
    if visible is None:
        return None
    rows = await db.execute(select(PurchaseOrder.id).where(PurchaseOrder.id.in_(visible)))
    return set(rows.scalars().all())


async def _visible_pr_ids(db: AsyncSession, actor: User):
    from app.core.scoping import visible_pr_id_subquery

    return await visible_pr_id_subquery(db, actor)


def _apply_status(stmt, column, filters: ExportFilters):
    if filters.statuses:
        stmt = stmt.where(column.in_(list(filters.statuses)))
    return stmt


# ===========================================================================
# 1. 采购申请 Purchase requisitions
# ===========================================================================

PR_FILTERS = frozenset({"date_range", "status", "department", "cost_center", "company", "keyword"})

PR_SHEETS = [
    ExportSheetSpec(
        title_zh="采购申请",
        title_en="Requisitions",
        total_column=10,
        columns=[
            _col("seq", "序号", "No.", lambda r: r[0], width=6),
            _col("pr_number", "申请单号", "PR No.", lambda r: r[1], width=16),
            _col("title", "标题", "Title", lambda r: r[2], width=32),
            _col("requester", "申请人", "Requester", lambda r: r[3]),
            _col("department", "部门", "Department", lambda r: r[4]),
            _col("cost_center", "成本中心", "Cost Center", lambda r: r[5], width=14),
            _col("company", "公司", "Company", lambda r: r[6], width=26),
            _col("status", "状态", "Status", lambda r: r[7], width=16),
            _col("currency", "币种", "Currency", lambda r: r[8], width=8),
            _col("item_count", "行数", "Lines", lambda r: r[9], width=8),
            _col(
                "total_amount",
                "总金额",
                "Amount",
                lambda r: r[10],
                field="purchase_requisition.total_amount",
            ),
            _col("required_date", "需求日期", "Required", lambda r: r[11], width=12),
            _col("expected_delivery", "期望到货", "Expected", lambda r: r[12], width=12),
            _col("submitted_at", "提交时间", "Submitted", lambda r: r[13], width=20),
            _col("created_at", "创建时间", "Created", lambda r: r[14], width=20),
        ],
    ),
    ExportSheetSpec(
        title_zh="申请行项目",
        title_en="Requisition Lines",
        columns=[
            _col("seq", "序号", "No.", lambda r: r[0], width=6),
            _col("pr_number", "申请单号", "PR No.", lambda r: r[1], width=16),
            _col("line_no", "行号", "Line", lambda r: r[2], width=6),
            _col("item_name", "物料", "Item", lambda r: r[3], width=32),
            _col("specification", "规格", "Specification", lambda r: r[4], width=32),
            _col("qty", "数量", "Qty", lambda r: r[5], width=10),
            _col("uom", "单位", "UOM", lambda r: r[6], width=8),
            _col(
                "unit_price",
                "单价",
                "Unit Price",
                lambda r: r[7],
                field="purchase_requisition.total_amount",
                width=14,
            ),
            _col(
                "amount",
                "金额",
                "Amount",
                lambda r: r[8],
                field="purchase_requisition.total_amount",
            ),
            _col("fulfilled_qty", "已履约数量", "Fulfilled", lambda r: r[9], width=14),
        ],
    ),
]


async def _load_prs(db: AsyncSession, request: ExportRequest) -> Sequence[list[list[Any]]]:
    filters = request.filters
    stmt: Select = (
        select(PurchaseRequisition)
        .options(
            selectinload(PurchaseRequisition.requester),
            selectinload(PurchaseRequisition.department),
            selectinload(PurchaseRequisition.cost_center),
            selectinload(PurchaseRequisition.company),
            selectinload(PurchaseRequisition.items).selectinload(PRItem.fulfillment_links),
        )
        .order_by(PurchaseRequisition.created_at.desc(), PurchaseRequisition.pr_number)
    )
    visible = await _visible_pr_ids(db, request.actor)
    if visible is not None:
        stmt = stmt.where(PurchaseRequisition.id.in_(visible))
    stmt = apply_date_range(stmt, PurchaseRequisition.created_at, filters)
    stmt = _apply_status(stmt, PurchaseRequisition.status, filters)
    if filters.department_id is not None:
        stmt = stmt.where(PurchaseRequisition.department_id == filters.department_id)
    if filters.cost_center_id is not None:
        stmt = stmt.where(PurchaseRequisition.cost_center_id == filters.cost_center_id)
    if filters.company_id is not None:
        stmt = stmt.where(PurchaseRequisition.company_id == filters.company_id)
    clause = keyword_clause(
        [PurchaseRequisition.pr_number, PurchaseRequisition.title], filters.keyword
    )
    if clause is not None:
        stmt = stmt.where(clause)

    prs = list((await db.execute(stmt)).scalars().all())

    header_rows: list[list[Any]] = []
    line_rows: list[list[Any]] = []
    for pr in prs:
        header_rows.append(
            [
                0,
                pr.pr_number,
                pr.title,
                pr.requester.display_name if pr.requester else "",
                pr.department.name_zh if pr.department else "",
                pr.cost_center.label_zh if pr.cost_center else "",
                pr.company.name_zh if pr.company else "",
                pr.status,
                pr.currency,
                len(pr.items),
                _num(pr.total_amount),
                _d(pr.required_date),
                _d(pr.expected_delivery_date),
                _d(pr.submitted_at),
                _d(pr.created_at),
            ]
        )
        for item in pr.items:
            line_rows.append(
                [
                    0,
                    pr.pr_number,
                    item.line_no,
                    item.item_name,
                    item.specification or "",
                    _num(item.qty),
                    item.uom,
                    _num(item.unit_price),
                    _num(item.amount),
                    _num(
                        sum(
                            (link.qty_contribution for link in item.fulfillment_links),
                            Decimal("0"),
                        )
                    ),
                ]
            )
    return [_with_index(header_rows), _with_index(line_rows)]


register(
    ExportDataset(
        key="purchase_requisitions",
        label_zh="采购申请",
        label_en="Purchase Requisitions",
        filters=PR_FILTERS,
        sheets=PR_SHEETS,
        loader=_load_prs,
        status_values=tuple(m.value for m in PRStatus),
    )
)


# ===========================================================================
# 2. 合同 Contracts
# ===========================================================================

CONTRACT_FILTERS = frozenset({"date_range", "status", "supplier", "keyword"})

CONTRACT_SHEETS = [
    ExportSheetSpec(
        title_zh="合同",
        title_en="Contracts",
        total_column=9,
        columns=[
            _col("seq", "序号", "No.", lambda r: r[0], width=6),
            _col("contract_number", "合同编号", "Contract No.", lambda r: r[1], width=22),
            _col("title", "标题", "Title", lambda r: r[2], width=32),
            _col("po_number", "采购订单号", "PO No.", lambda r: r[3], width=16),
            _col("supplier", "供应商", "Supplier", lambda r: r[4], width=30),
            _col("status", "状态", "Status", lambda r: r[5], width=14),
            _col("version", "版本", "Version", lambda r: r[6], width=8),
            _col("currency", "币种", "Currency", lambda r: r[7], width=8),
            _col("linked_pos", "关联订单数", "Linked POs", lambda r: r[8], width=12),
            _col(
                "total_amount",
                "总金额",
                "Amount",
                lambda r: r[9],
                field="contract.total_amount",
            ),
            _col("signed_date", "签订日期", "Signed", lambda r: r[10], width=12),
            _col("effective_date", "生效日期", "Effective", lambda r: r[11], width=12),
            _col("expiry_date", "到期日期", "Expiry", lambda r: r[12], width=12),
            _col("notes", "备注", "Notes", lambda r: r[13], field="contract.notes", width=30),
            _col("created_at", "创建时间", "Created", lambda r: r[14], width=20),
        ],
    ),
    ExportSheetSpec(
        title_zh="关联采购订单",
        title_en="Linked Purchase Orders",
        columns=[
            _col("seq", "序号", "No.", lambda r: r[0], width=6),
            _col("contract_number", "合同编号", "Contract No.", lambda r: r[1], width=22),
            _col("po_number", "采购订单号", "PO No.", lambda r: r[2], width=16),
            _col("po_status", "订单状态", "PO Status", lambda r: r[3], width=16),
            _col("relation", "关联方式", "Relation", lambda r: r[4], width=16),
        ],
    ),
]


async def _load_contracts(db: AsyncSession, request: ExportRequest) -> Sequence[list[list[Any]]]:
    filters = request.filters
    stmt: Select = (
        select(Contract)
        .options(
            selectinload(Contract.supplier),
            selectinload(Contract.po),
            selectinload(Contract.po_links).selectinload(POContractLink.po),
        )
        .order_by(Contract.created_at.desc(), Contract.contract_number)
    )
    visible_ids = await _visible_po_id_set(db, request.actor)
    if visible_ids is not None:
        stmt = stmt.where(Contract.po_id.in_(visible_ids))
    stmt = apply_date_range(stmt, Contract.created_at, filters)
    stmt = _apply_status(stmt, Contract.status, filters)
    if filters.supplier_id is not None:
        stmt = stmt.where(Contract.supplier_id == filters.supplier_id)
    clause = keyword_clause([Contract.contract_number, Contract.title], filters.keyword)
    if clause is not None:
        stmt = stmt.where(clause)

    contracts = list((await db.execute(stmt)).scalars().all())

    header_rows: list[list[Any]] = []
    link_rows: list[list[Any]] = []
    for contract in contracts:
        links: list[tuple[str, str, str]] = []
        if contract.po is not None and (visible_ids is None or contract.po.id in visible_ids):
            links.append((contract.po.po_number, contract.po.status, "primary"))
        for link in contract.po_links:
            if link.po is None or link.po.id == contract.po_id:
                continue
            # A link may point at a PO outside the actor's scope; emitting it
            # would leak that PO's number and status.
            if visible_ids is not None and link.po.id not in visible_ids:
                continue
            links.append((link.po.po_number, link.po.status, "linked"))
        header_rows.append(
            [
                0,
                contract.contract_number,
                contract.title,
                contract.po.po_number if contract.po else "",
                contract.supplier.name if contract.supplier else "",
                contract.status,
                contract.current_version,
                contract.currency,
                len(links),
                _num(contract.total_amount),
                _d(contract.signed_date),
                _d(contract.effective_date),
                _d(contract.expiry_date),
                contract.notes or "",
                _d(contract.created_at),
            ]
        )
        for po_number, po_status, relation in links:
            link_rows.append([0, contract.contract_number, po_number, po_status, relation])

    return [_with_index(header_rows), _with_index(link_rows)]


register(
    ExportDataset(
        key="contracts",
        label_zh="合同",
        label_en="Contracts",
        filters=CONTRACT_FILTERS,
        sheets=CONTRACT_SHEETS,
        loader=_load_contracts,
        status_values=tuple(m.value for m in ContractStatus),
    )
)


# ===========================================================================
# 3. 交货计划 Delivery plans
# ===========================================================================

PLAN_FILTERS = frozenset({"date_range", "status", "supplier", "keyword"})

PLAN_SHEETS = [
    ExportSheetSpec(
        title_zh="交货计划",
        title_en="Delivery Plans",
        columns=[
            _col("seq", "序号", "No.", lambda r: r[0], width=6),
            _col("plan_name", "计划名称", "Plan", lambda r: r[1], width=28),
            _col("po_number", "采购订单号", "PO No.", lambda r: r[2], width=16),
            _col("contract_number", "合同编号", "Contract No.", lambda r: r[3], width=22),
            _col("item", "物料", "Item", lambda r: r[4], width=30),
            _col("planned_qty", "计划数量", "Planned Qty", lambda r: r[5], width=12),
            _col("planned_date", "计划日期", "Planned Date", lambda r: r[6], width=14),
            _col("actual_qty", "实际数量", "Actual Qty", lambda r: r[7], width=12),
            _col("actual_date", "实际日期", "Actual Date", lambda r: r[8], width=14),
            _col("status", "状态", "Status", lambda r: r[9], width=14),
            _col("supplier", "供应商", "Supplier", lambda r: r[10], width=28),
            _col("notes", "备注", "Notes", lambda r: r[11], width=30),
            _col("created_at", "创建时间", "Created", lambda r: r[12], width=20),
        ],
    ),
]


async def _load_delivery_plans(
    db: AsyncSession, request: ExportRequest
) -> Sequence[list[list[Any]]]:
    filters = request.filters
    stmt: Select = (
        select(DeliveryPlan)
        .options(
            selectinload(DeliveryPlan.po).selectinload(PurchaseOrder.supplier),
            selectinload(DeliveryPlan.contract).selectinload(Contract.supplier),
            selectinload(DeliveryPlan.item),
        )
        .order_by(DeliveryPlan.planned_date.asc(), DeliveryPlan.plan_name)
    )
    visible = await _visible_po_ids(db, request.actor)
    if visible is not None:
        # A plan hangs off either a PO or, for contract-only plans, a contract
        # whose primary PO decides visibility.
        stmt = stmt.where(
            or_(
                DeliveryPlan.po_id.in_(visible),
                DeliveryPlan.contract_id.in_(
                    select(Contract.id).where(Contract.po_id.in_(visible))
                ),
            )
        )
    stmt = apply_date_range(stmt, DeliveryPlan.planned_date, filters, use_date=True)
    stmt = _apply_status(stmt, DeliveryPlan.status, filters)
    clause = keyword_clause([DeliveryPlan.plan_name, DeliveryPlan.notes], filters.keyword)
    if clause is not None:
        stmt = stmt.where(clause)

    plans = list((await db.execute(stmt)).scalars().all())
    if filters.supplier_id is not None:
        plans = [
            plan
            for plan in plans
            if (plan.po is not None and plan.po.supplier_id == filters.supplier_id)
            or (plan.contract is not None and plan.contract.supplier_id == filters.supplier_id)
        ]

    rows: list[list[Any]] = []
    for plan in plans:
        supplier = ""
        if plan.po is not None and plan.po.supplier is not None:
            supplier = plan.po.supplier.name
        elif plan.contract is not None and plan.contract.supplier is not None:
            supplier = plan.contract.supplier.name
        # DeliveryPlan stores no actuals: they are derived from shipments. Reuse
        # the helper the delivery-plan page uses so the export and the UI agree
        # (at the cost of two indexed queries per plan, which is fine at this
        # system's volume).
        from app.services.delivery_plans import _get_actual_qty_for_plan

        actual_qty, actual_date = await _get_actual_qty_for_plan(db, plan)
        rows.append(
            [
                0,
                plan.plan_name,
                plan.po.po_number if plan.po else "",
                plan.contract.contract_number if plan.contract else "",
                plan.item.name if plan.item else "",
                plan.planned_qty,
                _d(plan.planned_date),
                actual_qty,
                _d(actual_date),
                plan.status,
                supplier,
                plan.notes or "",
                _d(plan.created_at),
            ]
        )
    return [_with_index(rows)]


register(
    ExportDataset(
        key="delivery_plans",
        label_zh="交货计划",
        label_en="Delivery Plans",
        filters=PLAN_FILTERS,
        sheets=PLAN_SHEETS,
        loader=_load_delivery_plans,
        status_values=tuple(m.value for m in DeliveryPlanStatus),
    )
)


# ===========================================================================
# 4. 到货收货 Shipments
# ===========================================================================

SHIPMENT_FILTERS = frozenset({"date_range", "status", "supplier", "keyword"})

SHIPMENT_SHEETS = [
    ExportSheetSpec(
        title_zh="到货收货",
        title_en="Shipments",
        total_column=15,
        columns=[
            _col("seq", "序号", "No.", lambda r: r[0], width=6),
            _col("shipment_number", "到货单号", "Shipment No.", lambda r: r[1], width=18),
            _col("batch_no", "批次", "Batch", lambda r: r[2], width=8),
            _col("po_number", "采购订单号", "PO No.", lambda r: r[3], width=16),
            _col("contract_number", "合同编号", "Contract No.", lambda r: r[4], width=22),
            _col("supplier", "供应商", "Supplier", lambda r: r[5], width=28),
            _col("status", "状态", "Status", lambda r: r[6], width=16),
            _col("carrier", "承运商", "Carrier", lambda r: r[7], width=16),
            _col("tracking_number", "运单号", "Tracking", lambda r: r[8], width=20),
            _col("line_no", "行号", "Line", lambda r: r[9], width=6),
            _col("item_name", "物料", "Item", lambda r: r[10], width=30),
            _col("qty_shipped", "发货数量", "Shipped", lambda r: r[11], width=12),
            _col("qty_received", "收货数量", "Received", lambda r: r[12], width=12),
            _col("expected_date", "预计到货", "Expected", lambda r: r[13], width=12),
            _col("actual_date", "实际到货", "Arrived", lambda r: r[14], width=12),
            _col(
                "unit_price",
                "单价",
                "Unit Price",
                lambda r: r[15],
                field="shipment.unit_price",
                width=14,
            ),
            _col("notes", "备注", "Notes", lambda r: r[16], width=28),
        ],
    ),
]


async def _load_shipments(db: AsyncSession, request: ExportRequest) -> Sequence[list[list[Any]]]:
    filters = request.filters
    stmt: Select = (
        select(Shipment)
        .options(
            selectinload(Shipment.items),
            selectinload(Shipment.po).selectinload(PurchaseOrder.supplier),
            selectinload(Shipment.contract),
        )
        .order_by(Shipment.created_at.desc(), Shipment.shipment_number)
    )
    visible = await _visible_po_ids(db, request.actor)
    if visible is not None:
        stmt = stmt.where(Shipment.po_id.in_(visible))
    stmt = apply_date_range(stmt, Shipment.actual_date, filters, use_date=True)
    stmt = _apply_status(stmt, Shipment.status, filters)
    if filters.supplier_id is not None:
        stmt = stmt.where(
            Shipment.po_id.in_(
                select(PurchaseOrder.id).where(PurchaseOrder.supplier_id == filters.supplier_id)
            )
        )
    clause = keyword_clause(
        [Shipment.shipment_number, Shipment.tracking_number, Shipment.carrier], filters.keyword
    )
    if clause is not None:
        stmt = stmt.where(clause)

    shipments = list((await db.execute(stmt)).scalars().all())

    rows: list[list[Any]] = []
    for shipment in shipments:
        supplier = shipment.po.supplier.name if shipment.po and shipment.po.supplier else ""
        for item in shipment.items:
            rows.append(
                [
                    0,
                    shipment.shipment_number,
                    shipment.batch_no,
                    shipment.po.po_number if shipment.po else "",
                    shipment.contract.contract_number if shipment.contract else "",
                    supplier,
                    shipment.status,
                    shipment.carrier or "",
                    shipment.tracking_number or "",
                    item.line_no,
                    item.item_name,
                    _num(item.qty_shipped),
                    _num(item.qty_received),
                    _d(shipment.expected_date),
                    _d(shipment.actual_date),
                    _num(item.unit_price),
                    shipment.notes or "",
                ]
            )
    return [_with_index(rows)]


register(
    ExportDataset(
        key="shipments",
        label_zh="到货收货",
        label_en="Shipments",
        filters=SHIPMENT_FILTERS,
        sheets=SHIPMENT_SHEETS,
        loader=_load_shipments,
        status_values=tuple(m.value for m in ShipmentStatus),
    )
)


# ===========================================================================
# 5. 发票 Invoices
# ===========================================================================

INVOICE_FILTERS = frozenset({"date_range", "status", "supplier", "keyword"})

INVOICE_SHEETS = [
    ExportSheetSpec(
        title_zh="发票",
        title_en="Invoices",
        total_column=7,
        columns=[
            _col("seq", "序号", "No.", lambda r: r[0], width=6),
            _col("internal_number", "内部编号", "Internal No.", lambda r: r[1], width=18),
            _col("invoice_number", "发票号码", "Invoice No.", lambda r: r[2], width=20),
            _col("supplier", "供应商", "Supplier", lambda r: r[3], width=28),
            _col("invoice_date", "发票日期", "Invoice Date", lambda r: r[4], width=12),
            _col("due_date", "到期日", "Due Date", lambda r: r[5], width=12),
            _col("status", "状态", "Status", lambda r: r[6], width=14),
            _col(
                "total_amount",
                "价税合计",
                "Total",
                lambda r: r[7],
                field="invoice.total_amount",
            ),
            _col(
                "subtotal", "不含税金额", "Subtotal", lambda r: r[8], field="invoice.total_amount"
            ),
            _col("tax_amount", "税额", "Tax", lambda r: r[9], field="invoice.total_amount"),
            _col("currency", "币种", "Currency", lambda r: r[10], width=8),
            _col("matched", "完全匹配", "Matched", lambda r: r[11], width=12),
            _col("line_count", "行数", "Lines", lambda r: r[12], width=8),
            _col("notes", "备注", "Notes", lambda r: r[13], field="invoice.notes", width=28),
            _col("created_at", "创建时间", "Created", lambda r: r[14], width=20),
        ],
    ),
    ExportSheetSpec(
        title_zh="发票行项目",
        title_en="Invoice Lines",
        columns=[
            _col("seq", "序号", "No.", lambda r: r[0], width=6),
            _col("internal_number", "内部编号", "Internal No.", lambda r: r[1], width=18),
            _col("invoice_number", "发票号码", "Invoice No.", lambda r: r[2], width=20),
            _col("line_no", "行号", "Line", lambda r: r[3], width=6),
            _col("po_number", "关联采购订单号", "PO No.", lambda r: r[4], width=16),
            _col("line_type", "类型", "Type", lambda r: r[5], width=12),
            _col("item_name", "物料", "Item", lambda r: r[6], width=30),
            _col("qty", "数量", "Qty", lambda r: r[7], width=10),
            _col(
                "unit_price",
                "单价",
                "Unit Price",
                lambda r: r[8],
                field="invoice.total_amount",
                width=14,
            ),
            _col(
                "subtotal",
                "小计",
                "Subtotal",
                lambda r: r[9],
                field="invoice.total_amount",
            ),
            _col("tax_amount", "税额", "Tax", lambda r: r[10], field="invoice.total_amount"),
        ],
    ),
]


async def _load_invoices(db: AsyncSession, request: ExportRequest) -> Sequence[list[list[Any]]]:
    filters = request.filters
    stmt: Select = (
        select(Invoice)
        .options(
            selectinload(Invoice.supplier),
            selectinload(Invoice.lines),
        )
        .order_by(Invoice.invoice_date.desc(), Invoice.internal_number)
    )
    visible_ids = await _visible_po_id_set(db, request.actor)
    if visible_ids is not None:
        stmt = stmt.where(
            Invoice.id.in_(
                select(InvoiceLine.invoice_id)
                .join(POItem, POItem.id == InvoiceLine.po_item_id)
                .where(POItem.po_id.in_(visible_ids))
            )
        )
    stmt = apply_date_range(stmt, Invoice.invoice_date, filters, use_date=True)
    stmt = _apply_status(stmt, Invoice.status, filters)
    if filters.supplier_id is not None:
        stmt = stmt.where(Invoice.supplier_id == filters.supplier_id)
    clause = keyword_clause(
        [Invoice.internal_number, Invoice.invoice_number, Invoice.tax_number], filters.keyword
    )
    if clause is not None:
        stmt = stmt.where(clause)

    invoices = list((await db.execute(stmt)).scalars().all())

    po_item_ids = [line.po_item_id for inv in invoices for line in inv.lines if line.po_item_id]
    po_number_by_item: dict[UUID, str] = {}
    if po_item_ids:
        item_stmt = (
            select(POItem.id, PurchaseOrder.po_number)
            .join(PurchaseOrder, PurchaseOrder.id == POItem.po_id)
            .where(POItem.id.in_(po_item_ids))
        )
        if visible_ids is not None:
            # An invoice is included when ANY line touches a visible PO, but its
            # other lines may sit on POs the actor cannot see.
            item_stmt = item_stmt.where(POItem.po_id.in_(visible_ids))
        rows = (await db.execute(item_stmt)).all()
        po_number_by_item = {row[0]: row[1] for row in rows}

    header_rows: list[list[Any]] = []
    line_rows: list[list[Any]] = []
    for invoice in invoices:
        header_rows.append(
            [
                0,
                invoice.internal_number,
                invoice.invoice_number,
                invoice.supplier.name if invoice.supplier else "",
                _d(invoice.invoice_date),
                _d(invoice.due_date),
                invoice.status,
                _num(invoice.total_amount),
                _num(invoice.subtotal),
                _num(invoice.tax_amount),
                invoice.currency,
                "Y" if invoice.is_fully_matched else "N",
                len(invoice.lines),
                invoice.notes or "",
                _d(invoice.created_at),
            ]
        )
        for line in invoice.lines:
            if visible_ids is not None and (
                line.po_item_id is None or line.po_item_id not in po_number_by_item
            ):
                continue
            line_rows.append(
                [
                    0,
                    invoice.internal_number,
                    invoice.invoice_number,
                    line.line_no,
                    po_number_by_item.get(line.po_item_id, "") if line.po_item_id else "",
                    line.line_type,
                    line.item_name,
                    _num(line.qty),
                    _num(line.unit_price),
                    _num(line.subtotal),
                    _num(line.tax_amount),
                ]
            )
    return [_with_index(header_rows), _with_index(line_rows)]


register(
    ExportDataset(
        key="invoices",
        label_zh="发票",
        label_en="Invoices",
        filters=INVOICE_FILTERS,
        sheets=INVOICE_SHEETS,
        loader=_load_invoices,
        status_values=tuple(m.value for m in InvoiceStatus),
    )
)


# ===========================================================================
# 6. SKU 行情 SKU price intelligence
# ===========================================================================

SKU_FILTERS = frozenset({"date_range", "supplier", "item", "category", "keyword"})

SKU_SHEETS = [
    ExportSheetSpec(
        title_zh="价格记录",
        title_en="Price Records",
        total_column=6,
        columns=[
            _col("seq", "序号", "No.", lambda r: r[0], width=6),
            _col("item_code", "物料编码", "Item Code", lambda r: r[1], width=16),
            _col("item_name", "物料", "Item", lambda r: r[2], width=30),
            _col("category", "分类", "Category", lambda r: r[3], width=14),
            _col("supplier", "供应商", "Supplier", lambda r: r[4], width=28),
            _col("quotation_date", "报价日期", "Quotation Date", lambda r: r[5], width=14),
            _col("price", "价格", "Price", lambda r: r[6], field="sku_price_record.price"),
            _col("currency", "币种", "Currency", lambda r: r[7], width=8),
            _col("source_type", "来源", "Source", lambda r: r[8], width=12),
            _col(
                "source_ref",
                "来源单号",
                "Source Ref",
                lambda r: r[9],
                field="sku_price_record.source_ref",
                width=18,
            ),
            _col(
                "notes", "备注", "Notes", lambda r: r[10], field="sku_price_record.notes", width=28
            ),
            _col("created_at", "创建时间", "Created", lambda r: r[11], width=20),
        ],
    ),
    ExportSheetSpec(
        title_zh="行情基准",
        title_en="Price Benchmarks",
        columns=[
            _col("seq", "序号", "No.", lambda r: r[0], width=6),
            _col("item_code", "物料编码", "Item Code", lambda r: r[1], width=16),
            _col("item_name", "物料", "Item", lambda r: r[2], width=30),
            _col("window_days", "窗口（天）", "Window", lambda r: r[3], width=12),
            _col("avg_price", "均价", "Avg", lambda r: r[4], field="sku_price_record.avg_price"),
            _col(
                "median_price",
                "中位价",
                "Median",
                lambda r: r[5],
                field="sku_price_record.median_price",
            ),
            _col("min_price", "最低价", "Min", lambda r: r[6], field="sku_price_record.min_price"),
            _col("max_price", "最高价", "Max", lambda r: r[7], field="sku_price_record.max_price"),
            _col("stddev", "标准差", "Stddev", lambda r: r[8], field="sku_price_record.stddev"),
            _col(
                "sample_size",
                "样本数",
                "Samples",
                lambda r: r[9],
                field="sku_price_record.sample_size",
            ),
            _col(
                "last_refreshed_at",
                "刷新时间",
                "Refreshed",
                lambda r: r[10],
                field="sku_price_record.last_refreshed_at",
                width=20,
            ),
        ],
    ),
    ExportSheetSpec(
        title_zh="价格异常",
        title_en="Price Anomalies",
        columns=[
            _col("seq", "序号", "No.", lambda r: r[0], width=6),
            _col("item_code", "物料编码", "Item Code", lambda r: r[1], width=16),
            _col("item_name", "物料", "Item", lambda r: r[2], width=30),
            _col(
                "observed_price",
                "观察价",
                "Observed",
                lambda r: r[3],
                field="sku_price_record.observed_price",
            ),
            _col(
                "baseline_avg_price",
                "基准均价",
                "Baseline",
                lambda r: r[4],
                field="sku_price_record.baseline_avg_price",
            ),
            _col(
                "deviation_pct",
                "偏离度%",
                "Deviation %",
                lambda r: r[5],
                field="sku_price_record.deviation_pct",
                width=12,
            ),
            _col("severity", "级别", "Severity", lambda r: r[6], width=10),
            _col(
                "status",
                "状态",
                "Status",
                lambda r: r[7],
                field="sku_price_record.status",
                width=12,
            ),
            _col("notes", "备注", "Notes", lambda r: r[8], width=28),
            _col("created_at", "创建时间", "Created", lambda r: r[9], width=20),
        ],
    ),
]


async def _load_sku_prices(db: AsyncSession, request: ExportRequest) -> Sequence[list[list[Any]]]:
    filters = request.filters

    items = list((await db.execute(select(Item))).scalars().all())
    item_by_id = {item.id: item for item in items}

    # The item-dimension filters (item / category / keyword) scope all three
    # sheets; supplier and date_range only mean something for individual price
    # records, because benchmarks and anomalies are per-item aggregates.
    item_clauses = []
    if filters.item_id is not None:
        item_clauses.append(Item.id == filters.item_id)
    if filters.category_id is not None:
        item_clauses.append(Item.category_id == filters.category_id)
    if filters.keyword:
        pattern = f"%{filters.keyword.strip()}%"
        item_clauses.append(or_(Item.code.ilike(pattern), Item.name.ilike(pattern)))

    scoped_item_ids: set[UUID] | None = None
    if item_clauses:
        scoped_item_ids = set(
            (await db.execute(select(Item.id).where(*item_clauses))).scalars().all()
        )

    price_stmt: Select = (
        select(SKUPriceRecord)
        .options(selectinload(SKUPriceRecord.supplier))
        .order_by(SKUPriceRecord.quotation_date.desc(), SKUPriceRecord.id)
    )
    price_stmt = apply_date_range(price_stmt, SKUPriceRecord.quotation_date, filters, use_date=True)
    if scoped_item_ids is not None:
        price_stmt = price_stmt.where(SKUPriceRecord.item_id.in_(scoped_item_ids))
    if filters.supplier_id is not None:
        price_stmt = price_stmt.where(SKUPriceRecord.supplier_id == filters.supplier_id)
    prices = list((await db.execute(price_stmt)).scalars().all())

    price_rows: list[list[Any]] = []
    for record in prices:
        item = item_by_id.get(record.item_id)
        price_rows.append(
            [
                0,
                item.code if item else "",
                item.name if item else "",
                (item.category if item else "") or "",
                record.supplier.name if record.supplier else "",
                _d(record.quotation_date),
                _num(record.price),
                record.currency,
                record.source_type,
                record.source_ref or "",
                record.notes or "",
                _d(record.created_at),
            ]
        )

    bench_stmt: Select = select(SKUPriceBenchmark).order_by(
        SKUPriceBenchmark.item_id, SKUPriceBenchmark.window_days
    )
    if scoped_item_ids is not None:
        bench_stmt = bench_stmt.where(SKUPriceBenchmark.item_id.in_(scoped_item_ids))
    benchmarks = list((await db.execute(bench_stmt)).scalars().all())
    window = await _window_days(db)
    if window is not None:
        benchmarks = [b for b in benchmarks if b.window_days == window]

    bench_rows: list[list[Any]] = []
    for benchmark in benchmarks:
        item = item_by_id.get(benchmark.item_id)
        bench_rows.append(
            [
                0,
                item.code if item else "",
                item.name if item else "",
                benchmark.window_days,
                _num(benchmark.avg_price),
                _num(benchmark.median_price),
                _num(benchmark.min_price),
                _num(benchmark.max_price),
                _num(benchmark.stddev),
                benchmark.sample_size,
                _d(benchmark.last_refreshed_at),
            ]
        )

    anomaly_stmt: Select = select(SKUPriceAnomaly).order_by(SKUPriceAnomaly.created_at.desc())
    if scoped_item_ids is not None:
        anomaly_stmt = anomaly_stmt.where(SKUPriceAnomaly.item_id.in_(scoped_item_ids))
    anomalies = list((await db.execute(anomaly_stmt)).scalars().all())
    anomaly_rows: list[list[Any]] = []
    for anomaly in anomalies:
        item = item_by_id.get(anomaly.item_id)
        anomaly_rows.append(
            [
                0,
                item.code if item else "",
                item.name if item else "",
                _num(anomaly.observed_price),
                _num(anomaly.baseline_avg_price),
                _num(anomaly.deviation_pct),
                anomaly.severity,
                anomaly.status,
                anomaly.notes or "",
                _d(anomaly.created_at),
            ]
        )

    return [
        _with_index(price_rows),
        _with_index(bench_rows),
        _with_index(anomaly_rows),
    ]


async def _window_days(db: AsyncSession) -> int | None:
    """The configured benchmark window, if the parameter exists."""
    from app.models import SystemParameter

    value = (
        await db.execute(
            select(SystemParameter.value).where(SystemParameter.key == "sku.benchmark_window_days")
        )
    ).scalar_one_or_none()
    return value if isinstance(value, int) else None


register(
    ExportDataset(
        key="sku_prices",
        label_zh="SKU 行情",
        label_en="SKU Price Intelligence",
        filters=SKU_FILTERS,
        sheets=SKU_SHEETS,
        loader=_load_sku_prices,
    )
)


# ===========================================================================
# 7. 主数据：供应商 Suppliers
# ===========================================================================

SUPPLIER_FILTERS = frozenset({"keyword"})

SUPPLIER_SHEETS = [
    ExportSheetSpec(
        title_zh="供应商",
        title_en="Suppliers",
        columns=[
            _col("seq", "序号", "No.", lambda r: r[0], width=6),
            _col("code", "供应商编码", "Code", lambda r: r[1], width=16),
            _col("name", "名称", "Name", lambda r: r[2], width=36),
            _col("contact_name", "联系人", "Contact", lambda r: r[3], width=14),
            _col("contact_phone", "电话", "Phone", lambda r: r[4], width=18),
            _col("contact_email", "邮箱", "Email", lambda r: r[5], width=26),
            _col(
                "tax_number",
                "税号",
                "Tax No.",
                lambda r: r[6],
                field="supplier.tax_number",
                width=22,
            ),
            _col(
                "payee_name",
                "收款户名",
                "Payee",
                lambda r: r[7],
                field="supplier.payee_name",
                width=28,
            ),
            _col(
                "payee_bank",
                "开户行",
                "Bank",
                lambda r: r[8],
                field="supplier.payee_bank",
                width=28,
            ),
            _col(
                "payee_bank_account",
                "银行账号",
                "Bank Account",
                lambda r: r[9],
                field="supplier.payee_bank_account",
                width=26,
            ),
            _col("enabled", "启用", "Enabled", lambda r: r[10], width=8),
            _col("notes", "备注", "Notes", lambda r: r[11], field="supplier.notes", width=28),
            _col("created_at", "创建时间", "Created", lambda r: r[12], width=20),
        ],
    ),
]


async def _load_suppliers(db: AsyncSession, request: ExportRequest) -> Sequence[list[list[Any]]]:
    stmt: Select = select(Supplier).where(Supplier.is_deleted.is_(False)).order_by(Supplier.code)
    clause = keyword_clause(
        [Supplier.code, Supplier.name, Supplier.contact_name], request.filters.keyword
    )
    if clause is not None:
        stmt = stmt.where(clause)

    suppliers = list((await db.execute(stmt)).scalars().all())
    rows = [
        [
            0,
            supplier.code,
            supplier.name,
            supplier.contact_name or "",
            supplier.contact_phone or "",
            supplier.contact_email or "",
            supplier.tax_number or "",
            supplier.payee_name or "",
            supplier.payee_bank or "",
            supplier.payee_bank_account or "",
            "Y" if supplier.is_enabled else "N",
            supplier.notes or "",
            _d(supplier.created_at),
        ]
        for supplier in suppliers
    ]
    return [_with_index(rows)]


register(
    ExportDataset(
        key="suppliers",
        label_zh="供应商",
        label_en="Suppliers",
        filters=SUPPLIER_FILTERS,
        sheets=SUPPLIER_SHEETS,
        loader=_load_suppliers,
    )
)


# ===========================================================================
# 8. 主数据：物料 Items
# ===========================================================================

ITEM_FILTERS = frozenset({"category", "keyword"})

ITEM_SHEETS = [
    ExportSheetSpec(
        title_zh="物料",
        title_en="Items",
        columns=[
            _col("seq", "序号", "No.", lambda r: r[0], width=6),
            _col("code", "物料编码", "Code", lambda r: r[1], width=18),
            _col("name", "名称", "Name", lambda r: r[2], width=36),
            _col("category", "分类", "Category", lambda r: r[3], width=16),
            _col("uom", "单位", "UOM", lambda r: r[4], width=8),
            _col("specification", "规格", "Specification", lambda r: r[5], width=40),
            _col("requires_serial", "需序列号", "Serial", lambda r: r[6], width=12),
            _col("enabled", "启用", "Enabled", lambda r: r[7], width=8),
            _col("created_at", "创建时间", "Created", lambda r: r[8], width=20),
        ],
    ),
]


async def _load_items(db: AsyncSession, request: ExportRequest) -> Sequence[list[list[Any]]]:
    stmt: Select = select(Item).where(Item.is_deleted.is_(False)).order_by(Item.code)
    if request.filters.category_id is not None:
        stmt = stmt.where(Item.category_id == request.filters.category_id)
    clause = keyword_clause([Item.code, Item.name, Item.specification], request.filters.keyword)
    if clause is not None:
        stmt = stmt.where(clause)

    items = list((await db.execute(stmt)).scalars().all())
    rows = [
        [
            0,
            item.code,
            item.name,
            item.category or "",
            item.uom,
            item.specification or "",
            "Y" if item.requires_serial else "N",
            "Y" if item.is_enabled else "N",
            _d(item.created_at),
        ]
        for item in items
    ]
    return [_with_index(rows)]


register(
    ExportDataset(
        key="items",
        label_zh="物料",
        label_en="Items",
        filters=ITEM_FILTERS,
        sheets=ITEM_SHEETS,
        loader=_load_items,
    )
)


# ===========================================================================
# 9. 采购台账 Procurement ledger (adapter over the v1.52.0 implementation)
# ===========================================================================

LEDGER_FILTERS = frozenset({"date_range", "status", "supplier", "keyword"})

_LEDGER_HEADERS = [
    ("seq", "序号", "No.", 6),
    ("pr_number", "申请单号", "PR No.", 16),
    ("requester", "申请人", "Requester", 18),
    ("cost_center", "成本中心", "Cost Center", 14),
    ("company", "公司", "Company", 28),
    ("supplier", "供应商", "Supplier", 30),
    ("contracts", "合同流程号", "Contract No.", 22),
    ("qty", "数量", "Qty", 10),
    ("unit_price", "单价", "Unit Price", 14),
    ("amount", "总金额", "Amount", 16),
    ("currency", "币种", "Currency", 8),
    ("po_number", "采购订单号", "PO No.", 16),
    ("payments", "采购付款单号", "Payment No.", 26),
    ("invoice_status", "开票状态", "Invoice Status", 18),
    ("delivery_status", "到货状态", "Delivery Status", 18),
    ("oa_payment", "OA付款单号", "OA Payment No.", 18),
    ("notes", "备注", "Notes", 30),
]

_LEDGER_PAYMENT_HEADERS = [
    ("seq", "序号", "No.", 6),
    ("po_number", "采购订单号", "PO No.", 16),
    ("payment_number", "付款单号", "Payment No.", 26),
    ("contracts", "合同流程号", "Contract No.", 22),
    ("installment", "期次", "Installment", 10),
    ("amount", "金额", "Amount", 14),
    ("currency", "币种", "Currency", 8),
    ("status", "状态", "Status", 12),
    ("due_date", "应付日期", "Due Date", 12),
    ("payment_date", "实付日期", "Paid Date", 12),
    ("method", "付款方式", "Method", 16),
    ("ref", "流水号", "Ref", 22),
    ("notes", "备注", "Notes", 24),
]

_LEDGER_INVOICE_HEADERS = [
    ("seq", "序号", "No.", 6),
    ("internal_number", "内部编号", "Internal No.", 18),
    ("invoice_number", "发票号码", "Invoice No.", 20),
    ("supplier", "供应商", "Supplier", 28),
    ("po_number", "关联采购订单号", "PO No.", 16),
    ("invoice_date", "发票日期", "Invoice Date", 12),
    ("amount", "金额", "Amount", 14),
    ("currency", "币种", "Currency", 8),
    ("status", "状态", "Status", 12),
    ("item_name", "行物料", "Line Item", 30),
    ("qty", "行数量", "Line Qty", 12),
    ("subtotal", "行金额", "Line Amount", 14),
]


def _index_columns(specs: Sequence[tuple[str, str, str, int]], offset: int = 0):
    return [
        _col(key, zh, en, (lambda i: lambda row: row[i])(index + offset), width=width)
        for index, (key, zh, en, width) in enumerate(specs)
    ]


LEDGER_SHEETS = [
    ExportSheetSpec(
        title_zh="采购台账",
        title_en="Ledger",
        columns=_index_columns(_LEDGER_HEADERS),
        total_column=9,
    ),
    ExportSheetSpec(
        title_zh="付款明细",
        title_en="Payments",
        columns=_index_columns(_LEDGER_PAYMENT_HEADERS, offset=0),
    ),
    ExportSheetSpec(
        title_zh="发票明细",
        title_en="Invoice Lines",
        columns=_index_columns(_LEDGER_INVOICE_HEADERS, offset=0),
    ),
]


async def _load_ledger(db: AsyncSession, request: ExportRequest) -> Sequence[list[list[Any]]]:
    # ``collect_procurement_ledger`` already applies row scoping and field
    # gating, so the columns above deliberately carry no ``field``.
    data = await collect_procurement_ledger(
        db,
        actor=request.actor,
        date_from=request.filters.date_from,
        date_to=request.filters.date_to,
        statuses=request.filters.statuses or None,
        supplier_id=request.filters.supplier_id,
        keyword=request.filters.keyword,
        max_rows=1_000_000,
    )
    return [data.ledger_rows, data.payment_rows, data.invoice_rows]


register(
    ExportDataset(
        key="procurement_ledger",
        label_zh="采购台账",
        label_en="Procurement Ledger",
        filters=LEDGER_FILTERS,
        sheets=LEDGER_SHEETS,
        loader=_load_ledger,
        status_values=tuple(m.value for m in POStatus),
    )
)


# ===========================================================================
# 10. 付款记录 Payments
# ===========================================================================

PAYMENT_FILTERS = frozenset({"date_range", "status", "supplier", "keyword"})

PAYMENT_SHEETS = [
    ExportSheetSpec(
        title_zh="付款记录",
        title_en="Payments",
        total_column=5,
        columns=[
            _col("seq", "序号", "No.", lambda r: r[0], width=6),
            _col("payment_number", "付款单号", "Payment No.", lambda r: r[1], width=26),
            _col("po_number", "采购订单号", "PO No.", lambda r: r[2], width=16),
            _col("contract_number", "合同编号", "Contract No.", lambda r: r[3], width=22),
            _col("installment", "期次", "Installment", lambda r: r[4], width=10),
            _col(
                "amount",
                "金额",
                "Amount",
                lambda r: r[5],
                field="payment_record.amount",
            ),
            _col(
                "currency",
                "币种",
                "Currency",
                lambda r: r[6],
                field="payment_record.currency",
                width=8,
            ),
            _col(
                "status", "状态", "Status", lambda r: r[7], field="payment_record.status", width=12
            ),
            _col(
                "due_date",
                "应付日期",
                "Due Date",
                lambda r: r[8],
                field="payment_record.due_date",
                width=12,
            ),
            _col(
                "payment_date",
                "实付日期",
                "Paid Date",
                lambda r: r[9],
                field="payment_record.payment_date",
                width=12,
            ),
            _col(
                "method",
                "付款方式",
                "Method",
                lambda r: r[10],
                field="payment_record.payment_method",
                width=16,
            ),
            _col(
                "ref",
                "流水号",
                "Ref",
                lambda r: r[11],
                field="payment_record.transaction_ref",
                width=22,
            ),
            _col("notes", "备注", "Notes", lambda r: r[12], field="payment_record.notes", width=28),
            _col("created_at", "创建时间", "Created", lambda r: r[13], width=20),
        ],
    ),
]


async def _load_payments(db: AsyncSession, request: ExportRequest) -> Sequence[list[list[Any]]]:
    filters = request.filters
    stmt: Select = (
        select(PaymentRecord)
        .options(
            selectinload(PaymentRecord.po).selectinload(PurchaseOrder.supplier),
            selectinload(PaymentRecord.contract),
        )
        .order_by(PaymentRecord.created_at.desc(), PaymentRecord.payment_number)
    )
    visible = await _visible_po_ids(db, request.actor)
    if visible is not None:
        stmt = stmt.where(PaymentRecord.po_id.in_(visible))
    stmt = apply_date_range(stmt, PaymentRecord.created_at, filters)
    stmt = _apply_status(stmt, PaymentRecord.status, filters)
    if filters.supplier_id is not None:
        stmt = stmt.where(
            PaymentRecord.po_id.in_(
                select(PurchaseOrder.id).where(PurchaseOrder.supplier_id == filters.supplier_id)
            )
        )
    clause = keyword_clause(
        [PaymentRecord.payment_number, PaymentRecord.transaction_ref], filters.keyword
    )
    if clause is not None:
        stmt = stmt.where(clause)

    payments = list((await db.execute(stmt)).scalars().all())
    rows = [
        [
            0,
            payment.payment_number,
            payment.po.po_number if payment.po else "",
            payment.contract.contract_number if payment.contract else "",
            payment.installment_no,
            _num(payment.amount),
            payment.currency,
            payment.status,
            _d(payment.due_date),
            _d(payment.payment_date),
            payment.payment_method,
            payment.transaction_ref or "",
            payment.notes or "",
            _d(payment.created_at),
        ]
        for payment in payments
    ]
    return [_with_index(rows)]


register(
    ExportDataset(
        key="payments",
        label_zh="付款记录",
        label_en="Payments",
        filters=PAYMENT_FILTERS,
        sheets=PAYMENT_SHEETS,
        loader=_load_payments,
        status_values=tuple(m.value for m in PaymentStatus),
    )
)
