# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnusedCallResult=false, reportArgumentType=false
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.models import AuditLog, SystemParameter, SystemParameterCategory, User
from app.services.system_params import SystemParamsService, system_params


@pytest.fixture
def svc() -> SystemParamsService:
    return SystemParamsService()


async def _alice(db) -> User:
    return (await db.execute(select(User).where(User.username == "alice"))).scalar_one()


async def _create_param(
    db,
    *,
    key: str | None = None,
    category: SystemParameterCategory = SystemParameterCategory.AUTH,
    value=1,
    data_type: str = "int",
    default_value=None,
    min_value=None,
    max_value=None,
    updated_by_id=None,
) -> SystemParameter:
    param = SystemParameter(
        key=key or f"test.param.{uuid4().hex}",
        category=category,
        value=value,
        data_type=data_type,
        default_value=value if default_value is None else default_value,
        min_value=min_value,
        max_value=max_value,
        description_zh="测试参数",
        description_en="Test parameter",
        updated_by_id=updated_by_id,
    )
    db.add(param)
    await db.flush()
    return param


async def test_get_int_returns_seeded_value(svc, seeded_db_session):
    value = await svc.get_int(seeded_db_session, "approval.amount_threshold_cny")
    assert value == 100000


async def test_get_returns_default_for_missing_key(svc, seeded_db_session):
    sentinel = object()
    result = await svc.get(seeded_db_session, "no.such.key", sentinel)
    assert result is sentinel


async def test_get_int_raises_for_missing_key(svc, seeded_db_session):
    with pytest.raises(HTTPException) as exc:
        await svc.get_int(seeded_db_session, "no.such.key")
    assert exc.value.status_code == 500
    assert "invalid_int" in str(exc.value.detail)


async def test_get_int_accepts_numeric_value(svc, seeded_db_session):
    result = await svc.get_int(seeded_db_session, "sku.critical_multiplier")
    assert result == 2


async def test_get_int_or_falls_back_to_default_when_missing(svc, seeded_db_session):
    result = await svc.get_int_or(seeded_db_session, "no.such.key", 42)
    assert result == 42


async def test_get_int_or_falls_back_for_bool_value(svc, seeded_db_session):
    param = await _create_param(
        seeded_db_session,
        value=True,
        data_type="bool",
        default_value=True,
    )

    result = await svc.get_int_or(seeded_db_session, param.key, 7)

    assert result == 7


async def test_get_decimal_converts_int_value(svc, seeded_db_session):
    result = await svc.get_decimal(seeded_db_session, "sku.critical_multiplier")
    assert result == Decimal("2")


async def test_get_decimal_raises_for_missing_key(svc, seeded_db_session):
    with pytest.raises(HTTPException) as exc:
        await svc.get_decimal(seeded_db_session, "no.such.key")
    assert exc.value.status_code == 500
    assert "invalid_decimal" in str(exc.value.detail)


async def test_get_decimal_raises_for_invalid_value(svc, seeded_db_session):
    param = await _create_param(
        seeded_db_session,
        value="not-a-number",
        data_type="decimal",
        default_value="1.00",
    )

    with pytest.raises(HTTPException) as exc:
        await svc.get_decimal(seeded_db_session, param.key)

    assert exc.value.status_code == 500
    assert "invalid_decimal" in str(exc.value.detail)


async def test_cache_returns_same_value_second_call(svc, seeded_db_session):
    v1 = await svc.get_int(seeded_db_session, "approval.amount_threshold_cny")
    v2 = await svc.get_int(seeded_db_session, "approval.amount_threshold_cny")
    assert v1 == v2 == 100000


async def test_invalidate_clears_cache_for_key(svc, seeded_db_session):
    await svc.get_int(seeded_db_session, "approval.amount_threshold_cny")
    svc.invalidate("approval.amount_threshold_cny")
    value = await svc.get_int(seeded_db_session, "approval.amount_threshold_cny")
    assert value == 100000


async def test_invalidate_all_clears_entire_cache(svc, seeded_db_session):
    await svc.get_int(seeded_db_session, "approval.amount_threshold_cny")
    await svc.get_int(seeded_db_session, "pagination.default_page_size")
    svc.invalidate()
    value1 = await svc.get_int(seeded_db_session, "approval.amount_threshold_cny")
    value2 = await svc.get_int(seeded_db_session, "pagination.default_page_size")
    assert value1 == 100000
    assert value2 == 50


async def test_get_all_returns_all_seeded_params(svc, seeded_db_session):
    rows = await svc.get_all(seeded_db_session)
    assert len(rows) >= 14
    keys = {row.key for row in rows}
    assert "approval.amount_threshold_cny" in keys


async def test_get_all_filters_by_category(svc, seeded_db_session):
    rows = await svc.get_all(seeded_db_session, category="sku")
    assert len(rows) >= 1
    assert all(row.category == "sku" for row in rows)


async def test_get_param_returns_full_row(svc, seeded_db_session):
    param = await svc.get_param(seeded_db_session, "approval.amount_threshold_cny")
    assert param is not None
    assert param.data_type == "int"
    assert param.default_value == 100000
    assert param.min_value == 0


async def test_get_param_returns_none_for_missing(svc, seeded_db_session):
    param = await svc.get_param(seeded_db_session, "no.such.key")
    assert param is None


async def test_update_existing_param_writes_audit_log_and_invalidates_cache(svc, seeded_db_session):
    actor = await _alice(seeded_db_session)
    await svc.get_int(seeded_db_session, "approval.amount_threshold_cny")

    updated = await svc.update(
        seeded_db_session,
        "approval.amount_threshold_cny",
        120000,
        str(actor.id),
    )
    audit = (
        (
            await seeded_db_session.execute(
                select(AuditLog)
                .where(AuditLog.resource_id == "approval.amount_threshold_cny")
                .order_by(AuditLog.occurred_at.desc())
            )
        )
        .scalars()
        .first()
    )

    assert updated.value == 120000
    assert updated.updated_by_id == actor.id
    assert await svc.get_int(seeded_db_session, "approval.amount_threshold_cny") == 120000
    assert audit is not None
    assert audit.event_type == "admin.system_parameter.updated"
    assert audit.metadata_json == {
        "key": "approval.amount_threshold_cny",
        "old_value": 100000,
        "new_value": 120000,
    }


async def test_update_rejects_missing_param(svc, seeded_db_session):
    actor = await _alice(seeded_db_session)

    with pytest.raises(HTTPException) as exc:
        await svc.update(seeded_db_session, "no.such.key", 1, str(actor.id))

    assert exc.value.status_code == 404
    assert exc.value.detail == "system_parameter.not_found:no.such.key"


async def test_update_rejects_invalid_int_type(svc, seeded_db_session):
    actor = await _alice(seeded_db_session)

    with pytest.raises(HTTPException) as exc:
        await svc.update(
            seeded_db_session,
            "approval.amount_threshold_cny",
            "not-an-int",
            str(actor.id),
        )

    assert exc.value.status_code == 400
    assert exc.value.detail == "system_parameter.invalid_type:approval.amount_threshold_cny:int"


async def test_update_rejects_value_below_minimum(svc, seeded_db_session):
    actor = await _alice(seeded_db_session)

    with pytest.raises(HTTPException) as exc:
        await svc.update(seeded_db_session, "approval.amount_threshold_cny", -1, str(actor.id))

    assert exc.value.status_code == 400
    assert exc.value.detail == "system_parameter.below_min:approval.amount_threshold_cny"


async def test_update_normalizes_decimal_value(svc, seeded_db_session):
    actor = await _alice(seeded_db_session)
    param = await _create_param(
        seeded_db_session,
        category=SystemParameterCategory.PAYMENT,
        value="1.00",
        data_type="decimal",
        default_value="1.00",
        min_value="0.50",
        max_value="10.00",
    )

    updated = await svc.update(seeded_db_session, param.key, "2.50", str(actor.id))

    assert updated.value == "2.50"
    assert await svc.get_decimal(seeded_db_session, param.key) == Decimal("2.50")


async def test_reset_restores_default_and_writes_audit_log(svc, seeded_db_session):
    actor = await _alice(seeded_db_session)
    await svc.update(seeded_db_session, "approval.amount_threshold_cny", 120000, str(actor.id))

    reset = await svc.reset(seeded_db_session, "approval.amount_threshold_cny", str(actor.id))
    audit = (
        (
            await seeded_db_session.execute(
                select(AuditLog)
                .where(
                    AuditLog.resource_id == "approval.amount_threshold_cny",
                    AuditLog.event_type == "admin.system_parameter.reset",
                )
                .order_by(AuditLog.occurred_at.desc())
            )
        )
        .scalars()
        .first()
    )

    assert reset.value == 100000
    assert await svc.get_int(seeded_db_session, "approval.amount_threshold_cny") == 100000
    assert audit is not None
    assert audit.metadata_json == {
        "key": "approval.amount_threshold_cny",
        "old_value": 120000,
        "new_value": 100000,
    }


async def test_module_level_singleton_exists():
    assert isinstance(system_params, SystemParamsService)
