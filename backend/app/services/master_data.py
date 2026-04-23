from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date, datetime
from decimal import Decimal
from typing import cast
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AuditLog,
    Company,
    Contract,
    Department,
    Invoice,
    Item,
    POItem,
    PRItem,
    PurchaseOrder,
    SKUPriceAnomaly,
    SKUPriceBenchmark,
    SKUPriceRecord,
    Supplier,
    User,
)
from app.schemas import (
    CompanyCreate,
    CompanyUpdate,
    DepartmentCreate,
    DepartmentUpdate,
    ItemCreate,
    ItemUpdate,
    SupplierCreate,
    SupplierUpdate,
)

JsonScalar = str | int | float | bool | None
JsonValue = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]
MasterDataValue = str | bool | UUID | None
DiffPayload = dict[str, dict[str, JsonValue]]


def _jsonable(value: object) -> JsonValue:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_jsonable(item) for item in value]
    if isinstance(value, Mapping):
        mapping = cast(Mapping[object, object], value)
        return {str(key): _jsonable(val) for key, val in mapping.items()}
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _record_change(
    diff: DiffPayload, field: str, old: MasterDataValue, new: MasterDataValue
) -> None:
    if old == new:
        return
    diff[field] = {"old": _jsonable(old), "new": _jsonable(new)}


async def _audit(
    db: AsyncSession,
    actor: User,
    *,
    event_type: str,
    resource_type: str,
    resource_id: str,
    metadata: dict[str, object] | None = None,
    comment: str | None = None,
) -> None:
    db.add(
        AuditLog(
            actor_id=actor.id,
            actor_name=actor.display_name,
            event_type=event_type,
            resource_type=resource_type,
            resource_id=resource_id,
            metadata_json=_jsonable(metadata) if metadata else None,
            comment=comment,
        )
    )


async def _exists(db: AsyncSession, stmt: Select[tuple[UUID]]) -> bool:
    return (await db.execute(stmt.limit(1))).scalar_one_or_none() is not None


async def _ensure_unique_code(
    db: AsyncSession,
    *,
    model: type[Supplier] | type[Item] | type[Company],
    entity_name: str,
    code: str,
    current_id: UUID | None = None,
) -> None:
    stmt = select(model.id).where(model.code == code)
    if current_id is not None:
        stmt = stmt.where(model.id != current_id)
    if await _exists(db, stmt):
        raise HTTPException(status_code=409, detail=f"{entity_name}.code_exists:{code}")


async def _ensure_unique_department_code(
    db: AsyncSession,
    *,
    company_id: UUID,
    code: str,
    current_id: UUID | None = None,
) -> None:
    stmt = select(Department.id).where(
        Department.company_id == company_id,
        Department.code == code,
    )
    if current_id is not None:
        stmt = stmt.where(Department.id != current_id)
    if await _exists(db, stmt):
        raise HTTPException(status_code=409, detail=f"departments.code_exists:{code}")


async def _validate_department_parent(
    db: AsyncSession,
    *,
    department_id: UUID | None,
    company_id: UUID,
    parent_id: UUID | None,
) -> None:
    if parent_id is None:
        return
    if department_id is not None and parent_id == department_id:
        raise HTTPException(status_code=409, detail="department.parent_cycle")

    parent = await db.get(Department, parent_id)
    if parent is None:
        raise HTTPException(status_code=404, detail="department.parent_not_found")
    if parent.company_id != company_id:
        raise HTTPException(status_code=409, detail="department.parent_company_mismatch")

    seen: set[UUID] = {parent.id}
    current = parent
    while current.parent_id is not None:
        if current.parent_id in seen:
            raise HTTPException(status_code=409, detail="department.parent_cycle")
        if department_id is not None and current.parent_id == department_id:
            raise HTTPException(status_code=409, detail="department.parent_cycle")
        seen.add(current.parent_id)
        next_parent = await db.get(Department, current.parent_id)
        if next_parent is None:
            break
        current = next_parent


async def create_supplier(db: AsyncSession, actor: User, payload: SupplierCreate) -> Supplier:
    await _ensure_unique_code(db, model=Supplier, entity_name="supplier", code=payload.code)
    supplier = Supplier(
        code=payload.code,
        name=payload.name,
        tax_number=payload.tax_number,
        contact_name=payload.contact_name,
        contact_phone=payload.contact_phone,
        contact_email=payload.contact_email,
        notes=payload.notes,
    )
    db.add(supplier)
    await db.flush()
    await _audit(
        db,
        actor,
        event_type="supplier.created",
        resource_type="supplier",
        resource_id=str(supplier.id),
        metadata={
            "new": {
                "code": payload.code,
                "name": payload.name,
                "tax_number": payload.tax_number,
                "contact_name": payload.contact_name,
                "contact_phone": payload.contact_phone,
                "contact_email": payload.contact_email,
                "notes": payload.notes,
            }
        },
    )
    await db.commit()
    await db.refresh(supplier)
    return supplier


async def update_supplier(
    db: AsyncSession,
    actor: User,
    supplier_id: UUID,
    payload: SupplierUpdate,
) -> Supplier:
    supplier = await db.get(Supplier, supplier_id)
    if supplier is None:
        raise HTTPException(status_code=404, detail="supplier.not_found")

    diff: DiffPayload = {}
    if "code" in payload.model_fields_set and payload.code is not None:
        await _ensure_unique_code(
            db,
            model=Supplier,
            entity_name="supplier",
            code=payload.code,
            current_id=supplier.id,
        )
        _record_change(diff, "code", supplier.code, payload.code)
        supplier.code = payload.code
    if "name" in payload.model_fields_set and payload.name is not None:
        _record_change(diff, "name", supplier.name, payload.name)
        supplier.name = payload.name
    if "tax_number" in payload.model_fields_set:
        _record_change(diff, "tax_number", supplier.tax_number, payload.tax_number)
        supplier.tax_number = payload.tax_number
    if "contact_name" in payload.model_fields_set:
        _record_change(diff, "contact_name", supplier.contact_name, payload.contact_name)
        supplier.contact_name = payload.contact_name
    if "contact_phone" in payload.model_fields_set:
        _record_change(diff, "contact_phone", supplier.contact_phone, payload.contact_phone)
        supplier.contact_phone = payload.contact_phone
    if "contact_email" in payload.model_fields_set:
        _record_change(diff, "contact_email", supplier.contact_email, payload.contact_email)
        supplier.contact_email = payload.contact_email
    if "notes" in payload.model_fields_set:
        _record_change(diff, "notes", supplier.notes, payload.notes)
        supplier.notes = payload.notes
    if diff:
        await db.flush()
        await _audit(
            db,
            actor,
            event_type="supplier.updated",
            resource_type="supplier",
            resource_id=str(supplier.id),
            metadata={"diff": diff},
        )
        await db.commit()
        await db.refresh(supplier)
    return supplier


async def delete_supplier(db: AsyncSession, actor: User, supplier_id: UUID, *, hard: bool) -> None:
    supplier = await db.get(Supplier, supplier_id)
    if supplier is None:
        raise HTTPException(status_code=404, detail="supplier.not_found")

    if hard:
        if await _exists(
            db, select(PurchaseOrder.id).where(PurchaseOrder.supplier_id == supplier.id)
        ):
            raise HTTPException(
                status_code=409,
                detail="supplier.has_purchase_orders; hard delete denied",
            )
        if await _exists(db, select(PRItem.id).where(PRItem.supplier_id == supplier.id)):
            raise HTTPException(status_code=409, detail="supplier.has_pr_items; hard delete denied")
        if await _exists(db, select(Contract.id).where(Contract.supplier_id == supplier.id)):
            raise HTTPException(
                status_code=409, detail="supplier.has_contracts; hard delete denied"
            )
        if await _exists(db, select(Invoice.id).where(Invoice.supplier_id == supplier.id)):
            raise HTTPException(status_code=409, detail="supplier.has_invoices; hard delete denied")
        if await _exists(
            db, select(SKUPriceRecord.id).where(SKUPriceRecord.supplier_id == supplier.id)
        ):
            raise HTTPException(
                status_code=409, detail="supplier.has_price_records; hard delete denied"
            )

        await _audit(
            db,
            actor,
            event_type="supplier.deleted",
            resource_type="supplier",
            resource_id=str(supplier.id),
            metadata={"hard_delete": True, "code": supplier.code},
        )
        await db.delete(supplier)
        await db.commit()
        return

    if supplier.is_active:
        supplier.is_active = False
        await db.flush()
        await _audit(
            db,
            actor,
            event_type="supplier.deactivated",
            resource_type="supplier",
            resource_id=str(supplier.id),
            metadata={"old": {"is_active": True}, "new": {"is_active": False}},
        )
        await db.commit()


async def create_item(db: AsyncSession, actor: User, payload: ItemCreate) -> Item:
    await _ensure_unique_code(db, model=Item, entity_name="item", code=payload.code)
    item = Item(
        code=payload.code,
        name=payload.name,
        category=payload.category,
        category_id=payload.category_id,
        uom=payload.uom,
        specification=payload.specification,
        requires_serial=payload.requires_serial,
    )
    db.add(item)
    await db.flush()
    await _audit(
        db,
        actor,
        event_type="item.created",
        resource_type="item",
        resource_id=str(item.id),
        metadata={
            "new": {
                "code": payload.code,
                "name": payload.name,
                "category": payload.category,
                "category_id": str(payload.category_id) if payload.category_id else None,
                "uom": payload.uom,
                "specification": payload.specification,
                "requires_serial": payload.requires_serial,
            }
        },
    )
    await db.commit()
    await db.refresh(item)
    return item


async def update_item(db: AsyncSession, actor: User, item_id: UUID, payload: ItemUpdate) -> Item:
    item = await db.get(Item, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="item.not_found")

    diff: DiffPayload = {}
    if "code" in payload.model_fields_set and payload.code is not None:
        await _ensure_unique_code(
            db,
            model=Item,
            entity_name="item",
            code=payload.code,
            current_id=item.id,
        )
        _record_change(diff, "code", item.code, payload.code)
        item.code = payload.code
    if "name" in payload.model_fields_set and payload.name is not None:
        _record_change(diff, "name", item.name, payload.name)
        item.name = payload.name
    if "category" in payload.model_fields_set:
        _record_change(diff, "category", item.category, payload.category)
        item.category = payload.category
    if "uom" in payload.model_fields_set and payload.uom is not None:
        _record_change(diff, "uom", item.uom, payload.uom)
        item.uom = payload.uom
    if "specification" in payload.model_fields_set:
        _record_change(diff, "specification", item.specification, payload.specification)
        item.specification = payload.specification
    if "requires_serial" in payload.model_fields_set and payload.requires_serial is not None:
        _record_change(diff, "requires_serial", item.requires_serial, payload.requires_serial)
        item.requires_serial = payload.requires_serial
    if "category_id" in payload.model_fields_set:
        old_val = str(item.category_id) if item.category_id else None
        new_val = str(payload.category_id) if payload.category_id else None
        _record_change(diff, "category_id", old_val, new_val)
        item.category_id = payload.category_id
    if "is_active" in payload.model_fields_set and payload.is_active is not None:
        _record_change(diff, "is_active", item.is_active, payload.is_active)
        item.is_active = payload.is_active
    if diff:
        await db.flush()
        await _audit(
            db,
            actor,
            event_type="item.updated",
            resource_type="item",
            resource_id=str(item.id),
            metadata={"diff": diff},
        )
        await db.commit()
        await db.refresh(item)
    return item


async def delete_item(db: AsyncSession, actor: User, item_id: UUID, *, hard: bool) -> None:
    item = await db.get(Item, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="item.not_found")

    if hard:
        if await _exists(db, select(POItem.id).where(POItem.item_id == item.id)):
            raise HTTPException(status_code=409, detail="item.has_po_items; hard delete denied")
        if await _exists(db, select(PRItem.id).where(PRItem.item_id == item.id)):
            raise HTTPException(status_code=409, detail="item.has_pr_items; hard delete denied")
        if await _exists(db, select(SKUPriceRecord.id).where(SKUPriceRecord.item_id == item.id)):
            raise HTTPException(
                status_code=409, detail="item.has_price_records; hard delete denied"
            )
        if await _exists(
            db, select(SKUPriceBenchmark.id).where(SKUPriceBenchmark.item_id == item.id)
        ):
            raise HTTPException(
                status_code=409, detail="item.has_price_benchmarks; hard delete denied"
            )
        if await _exists(db, select(SKUPriceAnomaly.id).where(SKUPriceAnomaly.item_id == item.id)):
            raise HTTPException(
                status_code=409, detail="item.has_price_anomalies; hard delete denied"
            )

        await _audit(
            db,
            actor,
            event_type="item.deleted",
            resource_type="item",
            resource_id=str(item.id),
            metadata={"hard_delete": True, "code": item.code},
        )
        await db.delete(item)
        await db.commit()
        return

    if item.is_active:
        item.is_active = False
        await db.flush()
        await _audit(
            db,
            actor,
            event_type="item.deactivated",
            resource_type="item",
            resource_id=str(item.id),
            metadata={"old": {"is_active": True}, "new": {"is_active": False}},
        )
        await db.commit()


async def create_company(db: AsyncSession, actor: User, payload: CompanyCreate) -> Company:
    await _ensure_unique_code(db, model=Company, entity_name="company", code=payload.code)
    company = Company(
        code=payload.code,
        name_zh=payload.name_zh,
        name_en=payload.name_en,
        default_locale=payload.default_locale,
        default_currency=payload.default_currency,
    )
    db.add(company)
    await db.flush()
    await _audit(
        db,
        actor,
        event_type="company.created",
        resource_type="company",
        resource_id=str(company.id),
        metadata={
            "new": {
                "code": payload.code,
                "name_zh": payload.name_zh,
                "name_en": payload.name_en,
                "default_locale": payload.default_locale,
                "default_currency": payload.default_currency,
            }
        },
    )
    await db.commit()
    await db.refresh(company)
    return company


async def update_company(
    db: AsyncSession,
    actor: User,
    company_id: UUID,
    payload: CompanyUpdate,
) -> Company:
    company = await db.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="company.not_found")

    diff: DiffPayload = {}
    if "code" in payload.model_fields_set and payload.code is not None:
        await _ensure_unique_code(
            db,
            model=Company,
            entity_name="company",
            code=payload.code,
            current_id=company.id,
        )
        _record_change(diff, "code", company.code, payload.code)
        company.code = payload.code
    if "name_zh" in payload.model_fields_set and payload.name_zh is not None:
        _record_change(diff, "name_zh", company.name_zh, payload.name_zh)
        company.name_zh = payload.name_zh
    if "name_en" in payload.model_fields_set:
        _record_change(diff, "name_en", company.name_en, payload.name_en)
        company.name_en = payload.name_en
    if "default_locale" in payload.model_fields_set and payload.default_locale is not None:
        _record_change(diff, "default_locale", company.default_locale, payload.default_locale)
        company.default_locale = payload.default_locale
    if "default_currency" in payload.model_fields_set and payload.default_currency is not None:
        _record_change(diff, "default_currency", company.default_currency, payload.default_currency)
        company.default_currency = payload.default_currency
    if "is_active" in payload.model_fields_set and payload.is_active is not None:
        _record_change(diff, "is_active", company.is_active, payload.is_active)
        company.is_active = payload.is_active
    if diff:
        await db.flush()
        await _audit(
            db,
            actor,
            event_type="company.updated",
            resource_type="company",
            resource_id=str(company.id),
            metadata={"diff": diff},
        )
        await db.commit()
        await db.refresh(company)
    return company


async def delete_company(db: AsyncSession, actor: User, company_id: UUID) -> None:
    company = await db.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="company.not_found")

    if company.is_active:
        company.is_active = False
        await db.flush()
        await _audit(
            db,
            actor,
            event_type="company.deactivated",
            resource_type="company",
            resource_id=str(company.id),
            metadata={"old": {"is_active": True}, "new": {"is_active": False}},
        )
        await db.commit()


async def create_department(db: AsyncSession, actor: User, payload: DepartmentCreate) -> Department:
    company = await db.get(Company, payload.company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="company.not_found")

    await _ensure_unique_department_code(db, company_id=payload.company_id, code=payload.code)
    await _validate_department_parent(
        db,
        department_id=None,
        company_id=payload.company_id,
        parent_id=payload.parent_id,
    )

    department = Department(
        company_id=payload.company_id,
        code=payload.code,
        name_zh=payload.name_zh,
        name_en=payload.name_en,
        parent_id=payload.parent_id,
    )
    db.add(department)
    await db.flush()
    await _audit(
        db,
        actor,
        event_type="department.created",
        resource_type="department",
        resource_id=str(department.id),
        metadata={
            "new": {
                "company_id": str(payload.company_id),
                "code": payload.code,
                "name_zh": payload.name_zh,
                "name_en": payload.name_en,
                "parent_id": str(payload.parent_id) if payload.parent_id else None,
            }
        },
    )
    await db.commit()
    await db.refresh(department)
    return department


async def update_department(
    db: AsyncSession,
    actor: User,
    department_id: UUID,
    payload: DepartmentUpdate,
) -> Department:
    department = await db.get(Department, department_id)
    if department is None:
        raise HTTPException(status_code=404, detail="department.not_found")

    if "code" in payload.model_fields_set and payload.code is not None:
        await _ensure_unique_department_code(
            db,
            company_id=department.company_id,
            code=payload.code,
            current_id=department.id,
        )
    if "parent_id" in payload.model_fields_set:
        await _validate_department_parent(
            db,
            department_id=department.id,
            company_id=department.company_id,
            parent_id=payload.parent_id,
        )

    diff: DiffPayload = {}
    if "code" in payload.model_fields_set and payload.code is not None:
        _record_change(diff, "code", department.code, payload.code)
        department.code = payload.code
    if "name_zh" in payload.model_fields_set and payload.name_zh is not None:
        _record_change(diff, "name_zh", department.name_zh, payload.name_zh)
        department.name_zh = payload.name_zh
    if "name_en" in payload.model_fields_set:
        _record_change(diff, "name_en", department.name_en, payload.name_en)
        department.name_en = payload.name_en
    if "parent_id" in payload.model_fields_set:
        _record_change(diff, "parent_id", department.parent_id, payload.parent_id)
        department.parent_id = payload.parent_id
    if diff:
        await db.flush()
        await _audit(
            db,
            actor,
            event_type="department.updated",
            resource_type="department",
            resource_id=str(department.id),
            metadata={"diff": diff},
        )
        await db.commit()
        await db.refresh(department)
    return department


async def delete_department(db: AsyncSession, actor: User, department_id: UUID) -> None:
    department = await db.get(Department, department_id)
    if department is None:
        raise HTTPException(status_code=404, detail="department.not_found")

    user_count = await db.scalar(
        select(func.count(User.id)).where(User.department_id == department.id)
    )
    if (user_count or 0) > 0:
        raise HTTPException(
            status_code=409,
            detail="department.has_users; deactivate blocked",
        )

    if department.is_active:
        department.is_active = False
        await db.flush()
        await _audit(
            db,
            actor,
            event_type="department.deactivated",
            resource_type="department",
            resource_id=str(department.id),
            metadata={"old": {"is_active": True}, "new": {"is_active": False}},
        )
        await db.commit()
