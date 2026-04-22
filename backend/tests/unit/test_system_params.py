import pytest
from fastapi import HTTPException

from app.services.system_params import SystemParamsService, system_params


@pytest.fixture
def svc() -> SystemParamsService:
    fresh = SystemParamsService()
    return fresh


async def test_get_int_returns_seeded_value(svc, db_session):
    value = await svc.get_int(db_session, "approval.amount_threshold_cny")
    assert value == 100000


async def test_get_returns_default_for_missing_key(svc, db_session):
    sentinel = object()
    result = await svc.get(db_session, "no.such.key", sentinel)
    assert result is sentinel


async def test_get_int_raises_for_missing_key(svc, db_session):
    with pytest.raises(HTTPException) as exc:
        await svc.get_int(db_session, "no.such.key")
    assert exc.value.status_code == 500
    assert "invalid_int" in str(exc.value.detail)


async def test_get_int_accepts_numeric_value(svc, db_session):
    """Python int is broad: JSONB stored "2" is accepted for int getter even if
    data_type is 'float', since seed values are whole numbers. The type guard
    only rejects bool and non-numeric values."""
    result = await svc.get_int(db_session, "sku.critical_multiplier")
    assert result == 2


async def test_get_int_or_falls_back_to_default_when_missing(svc, db_session):
    result = await svc.get_int_or(db_session, "no.such.key", 42)
    assert result == 42


async def test_get_decimal_converts_int_value(svc, db_session):
    from decimal import Decimal

    result = await svc.get_decimal(db_session, "sku.critical_multiplier")
    assert result == Decimal("2")


async def test_get_decimal_raises_for_missing_key(svc, db_session):
    with pytest.raises(HTTPException) as exc:
        await svc.get_decimal(db_session, "no.such.key")
    assert exc.value.status_code == 500
    assert "invalid_decimal" in str(exc.value.detail)


async def test_cache_returns_same_value_second_call(svc, db_session):
    v1 = await svc.get_int(db_session, "approval.amount_threshold_cny")
    v2 = await svc.get_int(db_session, "approval.amount_threshold_cny")
    assert v1 == v2 == 100000


async def test_invalidate_clears_cache_for_key(svc, db_session):
    await svc.get_int(db_session, "approval.amount_threshold_cny")
    svc.invalidate("approval.amount_threshold_cny")
    v = await svc.get_int(db_session, "approval.amount_threshold_cny")
    assert v == 100000


async def test_invalidate_all_clears_entire_cache(svc, db_session):
    await svc.get_int(db_session, "approval.amount_threshold_cny")
    await svc.get_int(db_session, "pagination.default_page_size")
    svc.invalidate()
    v1 = await svc.get_int(db_session, "approval.amount_threshold_cny")
    v2 = await svc.get_int(db_session, "pagination.default_page_size")
    assert v1 == 100000
    assert v2 == 50


async def test_get_all_returns_all_seeded_params(svc, db_session):
    rows = await svc.get_all(db_session)
    assert len(rows) >= 14
    keys = {r.key for r in rows}
    assert "approval.amount_threshold_cny" in keys


async def test_get_all_filters_by_category(svc, db_session):
    rows = await svc.get_all(db_session, category="sku")
    assert len(rows) >= 1
    assert all(r.category == "sku" for r in rows)


async def test_get_param_returns_full_row(svc, db_session):
    param = await svc.get_param(db_session, "approval.amount_threshold_cny")
    assert param is not None
    assert param.data_type == "int"
    assert param.default_value == 100000
    assert param.min_value == 0


async def test_get_param_returns_none_for_missing(svc, db_session):
    param = await svc.get_param(db_session, "no.such.key")
    assert param is None


async def test_module_level_singleton_exists():
    assert isinstance(system_params, SystemParamsService)
