# pyright: reportMissingParameterType=false, reportOptionalSubscript=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownVariableType=false, reportUnusedCallResult=false

from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.models import (
    AuditLog,
    Company,
    Department,
    Item,
    PRItem,
    ProcurementCategory,
    PurchaseRequisition,
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
from app.services import master_data as svc


def _suffix() -> str:
    return uuid4().hex[:8].upper()


async def _user(seeded_db_session, username: str) -> User:
    return (
        await seeded_db_session.execute(select(User).where(User.username == username))
    ).scalar_one()


async def _category(seeded_db_session, code: str) -> ProcurementCategory:
    return (
        await seeded_db_session.execute(
            select(ProcurementCategory).where(ProcurementCategory.code == code)
        )
    ).scalar_one()


async def _supplier_by_code(seeded_db_session, code: str) -> Supplier:
    return (
        await seeded_db_session.execute(select(Supplier).where(Supplier.code == code))
    ).scalar_one()


async def _item_by_code(seeded_db_session, code: str) -> Item:
    return (await seeded_db_session.execute(select(Item).where(Item.code == code))).scalar_one()


async def _audit_logs(seeded_db_session, *, event_type: str, resource_id: str) -> list[AuditLog]:
    return list(
        (
            await seeded_db_session.execute(
                select(AuditLog)
                .where(
                    AuditLog.event_type == event_type,
                    AuditLog.resource_id == resource_id,
                )
                .order_by(AuditLog.occurred_at)
            )
        )
        .scalars()
        .all()
    )


async def _create_pr_with_line(
    seeded_db_session,
    *,
    requester: User,
    supplier_id=None,
    item_id=None,
) -> PRItem:
    pr = PurchaseRequisition(
        pr_number=f"PR-UT-{_suffix()}",
        title="Unit test PR",
        requester_id=requester.id,
        company_id=requester.company_id,
        department_id=requester.department_id,
        currency="CNY",
        total_amount=Decimal("1"),
    )
    seeded_db_session.add(pr)
    await seeded_db_session.flush()

    pr_item = PRItem(
        pr_id=pr.id,
        line_no=1,
        item_id=item_id,
        item_name="Linked item",
        supplier_id=supplier_id,
        qty=Decimal("1"),
        uom="EA",
        unit_price=Decimal("1"),
        amount=Decimal("1"),
    )
    seeded_db_session.add(pr_item)
    await seeded_db_session.flush()
    return pr_item


async def test_create_supplier_success_persists_and_audits(seeded_db_session):
    actor = await _user(seeded_db_session, "alice")
    payload = SupplierCreate(
        code=f"SUP-{_suffix()}",
        name="Test Supplier",
        tax_number="91310000MA1KTEST01",
        contact_name="Jane",
        contact_phone="13800000000",
        contact_email="supplier@example.com",
        notes="created by unit test",
    )

    supplier = await svc.create_supplier(seeded_db_session, actor, payload)

    assert supplier.code == payload.code
    assert supplier.name == payload.name
    assert supplier.is_enabled is True

    persisted = await _supplier_by_code(seeded_db_session, payload.code)
    assert persisted.id == supplier.id

    audits = await _audit_logs(
        seeded_db_session,
        event_type="supplier.created",
        resource_id=str(supplier.id),
    )
    assert len(audits) == 1
    assert audits[0].actor_id == actor.id
    assert audits[0].metadata_json["new"]["code"] == payload.code


async def test_create_supplier_normalizes_code_to_uppercase(seeded_db_session):
    actor = await _user(seeded_db_session, "alice")

    supplier = await svc.create_supplier(
        seeded_db_session,
        actor,
        SupplierCreate(code=f"sup-{_suffix().lower()}", name="Normalized Supplier"),
    )

    assert supplier.code.startswith("SUP-")
    assert supplier.code == supplier.code.upper()


async def test_create_supplier_duplicate_code_returns_409(seeded_db_session):
    actor = await _user(seeded_db_session, "alice")

    with pytest.raises(HTTPException) as exc:
        await svc.create_supplier(
            seeded_db_session,
            actor,
            SupplierCreate(code="sup-dell", name="Duplicate Dell"),
        )

    assert exc.value.status_code == 409
    assert exc.value.detail == "supplier.code_exists:SUP-DELL"


async def test_update_supplier_success_updates_fields_and_audits_diff(seeded_db_session):
    actor = await _user(seeded_db_session, "alice")
    supplier = await _supplier_by_code(seeded_db_session, "SUP-DELL")

    updated = await svc.update_supplier(
        seeded_db_session,
        actor,
        supplier.id,
        SupplierUpdate(
            name="Dell Updated",
            contact_email="updated@dell-demo.local",
            notes="changed by update",
        ),
    )

    assert updated.name == "Dell Updated"
    assert updated.contact_email == "updated@dell-demo.local"
    assert updated.notes == "changed by update"

    audits = await _audit_logs(
        seeded_db_session,
        event_type="supplier.updated",
        resource_id=str(supplier.id),
    )
    assert len(audits) == 1
    diff = audits[0].metadata_json["diff"]
    assert diff["name"] == {
        "old": "戴尔（中国）有限公司 / Dell China Ltd.",
        "new": "Dell Updated",
    }
    assert diff["contact_email"] == {
        "old": "sales@dell-demo.local",
        "new": "updated@dell-demo.local",
    }
    assert diff["notes"] == {"old": None, "new": "changed by update"}


async def test_update_supplier_not_found_returns_404(seeded_db_session):
    actor = await _user(seeded_db_session, "alice")

    with pytest.raises(HTTPException) as exc:
        await svc.update_supplier(
            seeded_db_session,
            actor,
            uuid4(),
            SupplierUpdate(name="Missing Supplier"),
        )

    assert exc.value.status_code == 404
    assert exc.value.detail == "supplier.not_found"


async def test_update_supplier_same_values_does_not_create_update_audit(seeded_db_session):
    actor = await _user(seeded_db_session, "alice")
    supplier = await _supplier_by_code(seeded_db_session, "SUP-LENOVO")

    updated = await svc.update_supplier(
        seeded_db_session,
        actor,
        supplier.id,
        SupplierUpdate(name=supplier.name),
    )

    assert updated.name == supplier.name
    audits = await _audit_logs(
        seeded_db_session,
        event_type="supplier.updated",
        resource_id=str(supplier.id),
    )
    assert audits == []


async def test_delete_supplier_soft_delete_deactivates_and_audits(seeded_db_session):
    actor = await _user(seeded_db_session, "alice")
    supplier = await svc.create_supplier(
        seeded_db_session,
        actor,
        SupplierCreate(code=f"SUP-{_suffix()}", name="Delete Me Supplier"),
    )

    await svc.delete_supplier(seeded_db_session, actor, supplier.id, hard=False)

    refreshed = await seeded_db_session.get(Supplier, supplier.id)
    assert refreshed is not None
    assert refreshed.is_deleted is True

    audits = await _audit_logs(
        seeded_db_session,
        event_type="supplier.deactivated",
        resource_id=str(supplier.id),
    )
    assert len(audits) == 1
    assert audits[0].metadata_json == {
        "old": {"is_deleted": False},
        "new": {"is_deleted": True},
    }


async def test_delete_supplier_hard_delete_blocked_by_fk_returns_409(seeded_db_session):
    actor = await _user(seeded_db_session, "alice")
    supplier = await _supplier_by_code(seeded_db_session, "SUP-APPLE")

    await _create_pr_with_line(
        seeded_db_session,
        requester=actor,
        supplier_id=supplier.id,
    )

    with pytest.raises(HTTPException) as exc:
        await svc.delete_supplier(seeded_db_session, actor, supplier.id, hard=True)

    assert exc.value.status_code == 409
    assert exc.value.detail == "supplier.has_pr_items; hard delete denied"


async def test_delete_supplier_not_found_returns_404(seeded_db_session):
    actor = await _user(seeded_db_session, "alice")

    with pytest.raises(HTTPException) as exc:
        await svc.delete_supplier(seeded_db_session, actor, uuid4(), hard=False)

    assert exc.value.status_code == 404
    assert exc.value.detail == "supplier.not_found"


async def test_create_item_success_with_category_id_and_audit(seeded_db_session):
    actor = await _user(seeded_db_session, "alice")
    category = await _category(seeded_db_session, "switch")
    payload = ItemCreate(
        code=f"ITEM-{_suffix()}",
        name="New Managed Switch",
        category="switch",
        category_id=category.id,
        uom="EA",
        specification="48-port managed switch",
        requires_serial=True,
    )

    item = await svc.create_item(seeded_db_session, actor, payload)

    assert item.code == payload.code
    assert item.category_id == category.id
    assert item.requires_serial is True

    audits = await _audit_logs(
        seeded_db_session,
        event_type="item.created",
        resource_id=str(item.id),
    )
    assert len(audits) == 1
    assert audits[0].metadata_json["new"]["category_id"] == str(category.id)


async def test_create_item_duplicate_code_returns_409(seeded_db_session):
    actor = await _user(seeded_db_session, "alice")

    with pytest.raises(HTTPException) as exc:
        await svc.create_item(
            seeded_db_session,
            actor,
            ItemCreate(code="sku-nb-t14", name="Duplicate ThinkPad"),
        )

    assert exc.value.status_code == 409
    assert exc.value.detail == "item.code_exists:SKU-NB-T14"


async def test_update_item_success_updates_multiple_fields_and_diff(seeded_db_session):
    actor = await _user(seeded_db_session, "alice")
    item = await _item_by_code(seeded_db_session, "SKU-NB-MBP16")

    updated = await svc.update_item(
        seeded_db_session,
        actor,
        item.id,
        ItemUpdate(
            name="MacBook Pro 16 M4 Max",
            specification="M4 Max, 64GB RAM, 2TB SSD",
            requires_serial=False,
        ),
    )

    assert updated.name == "MacBook Pro 16 M4 Max"
    assert updated.specification == "M4 Max, 64GB RAM, 2TB SSD"
    assert updated.requires_serial is False

    audits = await _audit_logs(
        seeded_db_session,
        event_type="item.updated",
        resource_id=str(item.id),
    )
    assert len(audits) == 1
    diff = audits[0].metadata_json["diff"]
    assert diff["name"]["new"] == "MacBook Pro 16 M4 Max"
    assert diff["specification"]["new"] == "M4 Max, 64GB RAM, 2TB SSD"
    assert diff["requires_serial"] == {"old": True, "new": False}


async def test_update_item_updates_category_id_and_records_string_diff(seeded_db_session):
    actor = await _user(seeded_db_session, "alice")
    item = await _item_by_code(seeded_db_session, "SRV-CPU-GOLD")
    target_category = await _category(seeded_db_session, "gpu")
    old_category_id = item.category_id

    updated = await svc.update_item(
        seeded_db_session,
        actor,
        item.id,
        ItemUpdate(category_id=target_category.id),
    )

    assert updated.category_id == target_category.id

    audits = await _audit_logs(
        seeded_db_session,
        event_type="item.updated",
        resource_id=str(item.id),
    )
    diff = audits[0].metadata_json["diff"]
    assert diff["category_id"]["old"] == str(old_category_id)
    assert diff["category_id"]["new"] == str(target_category.id)


async def test_update_item_updates_is_active(seeded_db_session):
    actor = await _user(seeded_db_session, "alice")
    item = await _item_by_code(seeded_db_session, "SKU-MON-U2723")

    updated = await svc.update_item(
        seeded_db_session,
        actor,
        item.id,
        ItemUpdate(is_enabled=False),
    )

    assert updated.is_enabled is False

    audits = await _audit_logs(
        seeded_db_session,
        event_type="item.updated",
        resource_id=str(item.id),
    )
    assert audits[0].metadata_json["diff"]["is_enabled"] == {
        "old": True,
        "new": False,
    }


async def test_update_item_not_found_returns_404(seeded_db_session):
    actor = await _user(seeded_db_session, "alice")

    with pytest.raises(HTTPException) as exc:
        await svc.update_item(
            seeded_db_session,
            actor,
            uuid4(),
            ItemUpdate(name="Missing Item"),
        )

    assert exc.value.status_code == 404
    assert exc.value.detail == "item.not_found"


async def test_delete_item_soft_delete_deactivates_and_audits(seeded_db_session):
    actor = await _user(seeded_db_session, "alice")
    item = await svc.create_item(
        seeded_db_session,
        actor,
        ItemCreate(code=f"ITEM-{_suffix()}", name="Delete Me Item"),
    )

    await svc.delete_item(seeded_db_session, actor, item.id, hard=False)

    refreshed = await seeded_db_session.get(Item, item.id)
    assert refreshed is not None
    assert refreshed.is_deleted is True

    audits = await _audit_logs(
        seeded_db_session,
        event_type="item.deactivated",
        resource_id=str(item.id),
    )
    assert len(audits) == 1
    assert audits[0].metadata_json == {
        "old": {"is_deleted": False},
        "new": {"is_deleted": True},
    }


async def test_delete_item_hard_delete_blocked_by_fk_returns_409(seeded_db_session):
    actor = await _user(seeded_db_session, "alice")
    item = await _item_by_code(seeded_db_session, "SKU-NB-T14")

    await _create_pr_with_line(
        seeded_db_session,
        requester=actor,
        item_id=item.id,
    )

    with pytest.raises(HTTPException) as exc:
        await svc.delete_item(seeded_db_session, actor, item.id, hard=True)

    assert exc.value.status_code == 409
    assert exc.value.detail == "item.has_pr_items; hard delete denied"


async def test_delete_item_not_found_returns_404(seeded_db_session):
    actor = await _user(seeded_db_session, "alice")

    with pytest.raises(HTTPException) as exc:
        await svc.delete_item(seeded_db_session, actor, uuid4(), hard=False)

    assert exc.value.status_code == 404
    assert exc.value.detail == "item.not_found"


async def test_create_company_success_persists_and_audits(seeded_db_session):
    actor = await _user(seeded_db_session, "alice")
    payload = CompanyCreate(
        code=f"comp-{_suffix().lower()}",
        name_zh="测试公司",
        name_en="Test Co",
        default_currency="CNY",
        default_locale="zh-CN",
    )

    company = await svc.create_company(seeded_db_session, actor, payload)

    assert company.code.startswith("COMP-")
    assert company.name_zh == payload.name_zh
    assert company.name_en == payload.name_en
    assert company.default_currency == "CNY"
    assert company.default_locale == "zh-CN"
    assert company.is_enabled is True

    persisted = (
        await seeded_db_session.execute(select(Company).where(Company.code == company.code))
    ).scalar_one()
    assert persisted.id == company.id

    audits = await _audit_logs(
        seeded_db_session,
        event_type="company.created",
        resource_id=str(company.id),
    )
    assert len(audits) == 1
    assert audits[0].metadata_json["new"]["code"] == company.code


async def test_update_company_success_updates_fields_and_audits_diff(seeded_db_session):
    actor = await _user(seeded_db_session, "alice")
    company = await svc.create_company(
        seeded_db_session,
        actor,
        CompanyCreate(
            code=f"COMP-{_suffix()}",
            name_zh="原公司",
            name_en="Original Co",
            default_currency="CNY",
            default_locale="zh-CN",
        ),
    )

    updated = await svc.update_company(
        seeded_db_session,
        actor,
        company.id,
        CompanyUpdate(
            name_zh="更新公司",
            name_en="Updated Co",
            default_currency="USD",
            default_locale="en-US",
        ),
    )

    assert updated.name_zh == "更新公司"
    assert updated.name_en == "Updated Co"
    assert updated.default_currency == "USD"
    assert updated.default_locale == "en-US"

    audits = await _audit_logs(
        seeded_db_session,
        event_type="company.updated",
        resource_id=str(company.id),
    )
    assert len(audits) == 1
    diff = audits[0].metadata_json["diff"]
    assert diff["name_zh"] == {"old": "原公司", "new": "更新公司"}
    assert diff["name_en"] == {"old": "Original Co", "new": "Updated Co"}
    assert diff["default_currency"] == {"old": "CNY", "new": "USD"}
    assert diff["default_locale"] == {"old": "zh-CN", "new": "en-US"}


async def test_update_company_not_found_returns_404(seeded_db_session):
    actor = await _user(seeded_db_session, "alice")

    with pytest.raises(HTTPException) as exc:
        await svc.update_company(
            seeded_db_session,
            actor,
            uuid4(),
            CompanyUpdate(name_zh="Missing Company"),
        )

    assert exc.value.status_code == 404
    assert exc.value.detail == "company.not_found"


async def test_delete_company_soft_delete_deactivates_and_audits(seeded_db_session):
    actor = await _user(seeded_db_session, "alice")
    company = await svc.create_company(
        seeded_db_session,
        actor,
        CompanyCreate(
            code=f"COMP-{_suffix()}",
            name_zh="待删除公司",
            name_en="Delete Company",
            default_currency="CNY",
            default_locale="zh-CN",
        ),
    )

    await svc.delete_company(seeded_db_session, actor, company.id)

    refreshed = await seeded_db_session.get(Company, company.id)
    assert refreshed is not None
    assert refreshed.is_deleted is True

    audits = await _audit_logs(
        seeded_db_session,
        event_type="company.deactivated",
        resource_id=str(company.id),
    )
    assert len(audits) == 1
    assert audits[0].metadata_json == {
        "old": {"is_deleted": False},
        "new": {"is_deleted": True},
    }


async def test_create_department_success_persists_and_audits(seeded_db_session):
    actor = await _user(seeded_db_session, "alice")
    company = await svc.create_company(
        seeded_db_session,
        actor,
        CompanyCreate(
            code=f"COMP-{_suffix()}",
            name_zh="部门所属公司",
            name_en="Department Company",
        ),
    )

    department = await svc.create_department(
        seeded_db_session,
        actor,
        DepartmentCreate(
            code=f"dept-{_suffix().lower()}",
            company_id=company.id,
            name_zh="测试部门",
            name_en="Test Department",
        ),
    )

    assert department.company_id == company.id
    assert department.code.startswith("DEPT-")
    assert department.name_zh == "测试部门"
    assert department.name_en == "Test Department"
    assert department.parent_id is None
    assert department.is_enabled is True

    persisted = (
        await seeded_db_session.execute(select(Department).where(Department.id == department.id))
    ).scalar_one()
    assert persisted.code == department.code

    audits = await _audit_logs(
        seeded_db_session,
        event_type="department.created",
        resource_id=str(department.id),
    )
    assert len(audits) == 1
    assert audits[0].metadata_json["new"]["company_id"] == str(company.id)


async def test_update_department_success_updates_fields_and_audits_diff(seeded_db_session):
    actor = await _user(seeded_db_session, "alice")
    company = await svc.create_company(
        seeded_db_session,
        actor,
        CompanyCreate(code=f"COMP-{_suffix()}", name_zh="更新部门公司", name_en="Dept Update Co"),
    )
    parent = await svc.create_department(
        seeded_db_session,
        actor,
        DepartmentCreate(
            code=f"PARENT-{_suffix()}",
            company_id=company.id,
            name_zh="父部门",
            name_en="Parent Department",
        ),
    )
    department = await svc.create_department(
        seeded_db_session,
        actor,
        DepartmentCreate(
            code=f"CHILD-{_suffix()}",
            company_id=company.id,
            name_zh="子部门",
            name_en="Child Department",
        ),
    )

    updated = await svc.update_department(
        seeded_db_session,
        actor,
        department.id,
        DepartmentUpdate(
            code=f"UPDATED-{_suffix()}",
            name_zh="已更新部门",
            name_en="Updated Department",
            parent_id=parent.id,
        ),
    )

    assert updated.code.startswith("UPDATED-")
    assert updated.name_zh == "已更新部门"
    assert updated.name_en == "Updated Department"
    assert updated.parent_id == parent.id

    audits = await _audit_logs(
        seeded_db_session,
        event_type="department.updated",
        resource_id=str(department.id),
    )
    assert len(audits) == 1
    diff = audits[0].metadata_json["diff"]
    assert diff["name_zh"] == {"old": "子部门", "new": "已更新部门"}
    assert diff["name_en"] == {"old": "Child Department", "new": "Updated Department"}
    assert diff["parent_id"] == {"old": None, "new": str(parent.id)}
    assert diff["code"]["old"].startswith("CHILD-")
    assert diff["code"]["new"].startswith("UPDATED-")


async def test_delete_department_soft_delete_deactivates_and_audits(seeded_db_session):
    actor = await _user(seeded_db_session, "alice")
    company = await svc.create_company(
        seeded_db_session,
        actor,
        CompanyCreate(code=f"COMP-{_suffix()}", name_zh="删除部门公司", name_en="Delete Dept Co"),
    )
    department = await svc.create_department(
        seeded_db_session,
        actor,
        DepartmentCreate(
            code=f"DEPT-{_suffix()}",
            company_id=company.id,
            name_zh="待删除部门",
            name_en="Delete Department",
        ),
    )

    await svc.delete_department(seeded_db_session, actor, department.id)

    refreshed = await seeded_db_session.get(Department, department.id)
    assert refreshed is not None
    assert refreshed.is_deleted is True

    audits = await _audit_logs(
        seeded_db_session,
        event_type="department.deactivated",
        resource_id=str(department.id),
    )
    assert len(audits) == 1
    assert audits[0].metadata_json == {
        "old": {"is_deleted": False},
        "new": {"is_deleted": True},
    }
