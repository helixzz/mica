# pyright: reportMissingParameterType=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownVariableType=false, reportUnusedCallResult=false

from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.models import CostCenter, LookupValue, ProcurementCategory
from app.services import classification as svc


def _suffix() -> str:
    return uuid4().hex[:8].upper()


async def _cost_center_by_code(seeded_db_session, code: str) -> CostCenter:
    return (
        await seeded_db_session.execute(select(CostCenter).where(CostCenter.code == code))
    ).scalar_one()


async def _category_by_code(seeded_db_session, code: str) -> ProcurementCategory:
    return (
        await seeded_db_session.execute(
            select(ProcurementCategory).where(ProcurementCategory.code == code)
        )
    ).scalar_one()


async def _lookup_value(seeded_db_session, *, type_: str, code: str) -> LookupValue:
    return (
        await seeded_db_session.execute(
            select(LookupValue).where(
                LookupValue.type == type_,
                LookupValue.code == code,
            )
        )
    ).scalar_one()


async def test_list_cost_centers_returns_seeded_active_rows(seeded_db_session):
    cost_centers = await svc.list_cost_centers(seeded_db_session)

    assert len(cost_centers) >= 4
    assert all(cost_center.is_enabled is True for cost_center in cost_centers)
    assert [cost_center.code for cost_center in cost_centers[:4]] == [
        "CC-IT",
        "CC-ADMIN",
        "CC-PROD",
        "CC-FIN",
    ]


async def test_create_cost_center_success(seeded_db_session):
    code = f"CC-{_suffix()}"

    created = await svc.create_cost_center(
        seeded_db_session,
        {
            "code": code,
            "label_zh": "新增成本中心",
            "label_en": "New Cost Center",
            "sort_order": 9,
        },
    )

    assert created.code == code
    assert created.is_enabled is True

    persisted = await _cost_center_by_code(seeded_db_session, code)
    assert persisted.id == created.id


async def test_update_cost_center_success(seeded_db_session):
    created = await svc.create_cost_center(
        seeded_db_session,
        {
            "code": f"CC-{_suffix()}",
            "label_zh": "原始",
            "label_en": "Original",
            "sort_order": 5,
        },
    )

    updated = await svc.update_cost_center(
        seeded_db_session,
        created.id,
        {"label_zh": "已更新", "label_en": "Updated", "sort_order": 6},
    )

    assert updated.label_zh == "已更新"
    assert updated.label_en == "Updated"
    assert updated.sort_order == 6


async def test_delete_cost_center_soft_delete_hides_from_active_list(seeded_db_session):
    created = await svc.create_cost_center(
        seeded_db_session,
        {
            "code": f"CC-{_suffix()}",
            "label_zh": "待删除",
            "label_en": "To Delete",
            "sort_order": 8,
        },
    )

    await svc.delete_cost_center(seeded_db_session, created.id)

    refreshed = await seeded_db_session.get(CostCenter, created.id)
    assert refreshed is not None
    assert refreshed.is_deleted is True

    active_codes = {
        cost_center.code for cost_center in await svc.list_cost_centers(seeded_db_session)
    }
    all_codes = {
        cost_center.code
        for cost_center in await svc.list_cost_centers(
            seeded_db_session, enabled_only=False, include_deleted=True
        )
    }
    assert created.code not in active_codes
    assert created.code in all_codes


async def test_update_cost_center_not_found_returns_404(seeded_db_session):
    with pytest.raises(HTTPException) as exc:
        await svc.update_cost_center(seeded_db_session, uuid4(), {"label_zh": "missing"})

    assert exc.value.status_code == 404
    assert exc.value.detail == "cost_center.not_found"


async def test_delete_cost_center_not_found_returns_404(seeded_db_session):
    with pytest.raises(HTTPException) as exc:
        await svc.delete_cost_center(seeded_db_session, uuid4())

    assert exc.value.status_code == 404
    assert exc.value.detail == "cost_center.not_found"


async def test_list_procurement_categories_flat_returns_seeded_rows(seeded_db_session):
    categories = await svc.list_procurement_categories(seeded_db_session, flat=True)

    assert len(categories) >= 10
    assert all(category.is_enabled is True for category in categories)
    assert any(category.code == "server" and category.level == 1 for category in categories)
    assert any(category.code == "memory" and category.level == 2 for category in categories)


async def test_create_procurement_category_level_one_success(seeded_db_session):
    code = f"L1-{_suffix()}"

    created = await svc.create_procurement_category(
        seeded_db_session,
        {
            "code": code,
            "label_zh": "一级分类",
            "label_en": "Level 1",
            "sort_order": 99,
        },
    )

    assert created.code == code
    assert created.level == 1
    assert created.parent_id is None


async def test_create_procurement_category_with_parent_creates_level_two(seeded_db_session):
    parent = await _category_by_code(seeded_db_session, "network")
    code = f"L2-{_suffix()}"

    created = await svc.create_procurement_category(
        seeded_db_session,
        {
            "code": code,
            "label_zh": "网络子类",
            "label_en": "Network Child",
            "sort_order": 7,
            "parent_id": parent.id,
        },
    )

    assert created.parent_id == parent.id
    assert created.level == parent.level + 1


async def test_create_procurement_category_missing_parent_returns_404(seeded_db_session):
    with pytest.raises(HTTPException) as exc:
        await svc.create_procurement_category(
            seeded_db_session,
            {
                "code": f"L2-{_suffix()}",
                "label_zh": "缺失父级",
                "label_en": "Missing Parent",
                "sort_order": 1,
                "parent_id": uuid4(),
            },
        )

    assert exc.value.status_code == 404
    assert exc.value.detail == "parent_category.not_found"


async def test_update_procurement_category_success(seeded_db_session):
    category = await svc.create_procurement_category(
        seeded_db_session,
        {
            "code": f"CAT-{_suffix()}",
            "label_zh": "原分类",
            "label_en": "Original Category",
            "sort_order": 2,
        },
    )

    updated = await svc.update_procurement_category(
        seeded_db_session,
        category.id,
        {"label_zh": "已更新分类", "label_en": "Updated Category", "sort_order": 3},
    )

    assert updated.label_zh == "已更新分类"
    assert updated.label_en == "Updated Category"
    assert updated.sort_order == 3


async def test_delete_procurement_category_soft_delete_filters_active_list(seeded_db_session):
    category = await svc.create_procurement_category(
        seeded_db_session,
        {
            "code": f"CAT-{_suffix()}",
            "label_zh": "待删除分类",
            "label_en": "Delete Category",
            "sort_order": 4,
        },
    )

    await svc.delete_procurement_category(seeded_db_session, category.id)

    refreshed = await seeded_db_session.get(ProcurementCategory, category.id)
    assert refreshed is not None
    assert refreshed.is_deleted is True

    active_codes = {
        procurement_category.code
        for procurement_category in await svc.list_procurement_categories(
            seeded_db_session, flat=True
        )
    }
    all_codes = {
        procurement_category.code
        for procurement_category in await svc.list_procurement_categories(
            seeded_db_session, active_only=False, flat=True
        )
    }
    assert category.code not in active_codes
    assert category.code in all_codes


async def test_update_procurement_category_not_found_returns_404(seeded_db_session):
    with pytest.raises(HTTPException) as exc:
        await svc.update_procurement_category(
            seeded_db_session,
            uuid4(),
            {"label_zh": "missing"},
        )

    assert exc.value.status_code == 404
    assert exc.value.detail == "category.not_found"


async def test_delete_procurement_category_not_found_returns_404(seeded_db_session):
    with pytest.raises(HTTPException) as exc:
        await svc.delete_procurement_category(seeded_db_session, uuid4())

    assert exc.value.status_code == 404
    assert exc.value.detail == "category.not_found"


async def test_get_category_tree_returns_only_level_one_with_nested_children(seeded_db_session):
    tree = await svc.get_category_tree(seeded_db_session)

    assert tree
    assert all(category.parent_id is None for category in tree)
    assert all(category.level == 1 for category in tree)

    server_parts = next(category for category in tree if category.code == "server_parts")
    child_codes = {child.code for child in server_parts.children}
    assert {"memory", "ssd", "cpu", "nic", "gpu", "psu"}.issubset(child_codes)
    assert all(child.parent_id == server_parts.id for child in server_parts.children)


async def test_list_lookup_values_returns_seeded_expense_types(seeded_db_session):
    values = await svc.list_lookup_values(seeded_db_session, "expense_type")

    assert [value.code for value in values] == ["capex", "opex"]
    assert all(value.is_enabled is True for value in values)


async def test_create_lookup_value_success(seeded_db_session):
    code = f"lookup-{_suffix().lower()}"

    created = await svc.create_lookup_value(
        seeded_db_session,
        {
            "type": "expense_type",
            "code": code,
            "label_zh": "测试值",
            "label_en": "Test Value",
            "sort_order": 10,
        },
    )

    assert created.code == code
    assert created.type == "expense_type"
    assert created.is_enabled is True

    persisted = await _lookup_value(seeded_db_session, type_="expense_type", code=code)
    assert persisted.id == created.id


async def test_update_lookup_value_success(seeded_db_session):
    created = await svc.create_lookup_value(
        seeded_db_session,
        {
            "type": "expense_type",
            "code": f"lookup-{_suffix().lower()}",
            "label_zh": "原值",
            "label_en": "Original Value",
            "sort_order": 11,
        },
    )

    updated = await svc.update_lookup_value(
        seeded_db_session,
        created.id,
        {"label_zh": "已更新值", "label_en": "Updated Value", "sort_order": 12},
    )

    assert updated.label_zh == "已更新值"
    assert updated.label_en == "Updated Value"
    assert updated.sort_order == 12


async def test_delete_lookup_value_soft_delete_filters_active_list(seeded_db_session):
    created = await svc.create_lookup_value(
        seeded_db_session,
        {
            "type": "expense_type",
            "code": f"lookup-{_suffix().lower()}",
            "label_zh": "待删除值",
            "label_en": "Delete Value",
            "sort_order": 13,
        },
    )

    await svc.delete_lookup_value(seeded_db_session, created.id)

    refreshed = await seeded_db_session.get(LookupValue, created.id)
    assert refreshed is not None
    assert refreshed.is_deleted is True

    active_codes = {
        lookup_value.code
        for lookup_value in await svc.list_lookup_values(seeded_db_session, "expense_type")
    }
    all_codes = {
        lookup_value.code
        for lookup_value in await svc.list_lookup_values(
            seeded_db_session, "expense_type", active_only=False
        )
    }
    assert created.code not in active_codes
    assert created.code in all_codes


async def test_update_lookup_value_not_found_returns_404(seeded_db_session):
    with pytest.raises(HTTPException) as exc:
        await svc.update_lookup_value(seeded_db_session, uuid4(), {"label_zh": "missing"})

    assert exc.value.status_code == 404
    assert exc.value.detail == "lookup_value.not_found"


async def test_delete_lookup_value_not_found_returns_404(seeded_db_session):
    with pytest.raises(HTTPException) as exc:
        await svc.delete_lookup_value(seeded_db_session, uuid4())

    assert exc.value.status_code == 404
    assert exc.value.detail == "lookup_value.not_found"
