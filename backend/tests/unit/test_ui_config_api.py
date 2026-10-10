"""API tests for GET /ui-config (the whitelisted UI system parameters)."""

from .test_export_ledger_api import _auth_headers, _client, _user


async def test_ui_config_requires_auth(seeded_db_session):
    async with _client(seeded_db_session) as client:
        resp = await client.get("/api/v1/ui-config")

    assert resp.status_code == 401


async def test_ui_config_returns_the_configured_default_page_size(seeded_db_session):
    """The parameter used to be seeded but read by nobody."""
    db = seeded_db_session
    actor = await _user(db)

    async with _client(db) as client:
        resp = await client.get("/api/v1/ui-config", headers=_auth_headers(actor))

    assert resp.status_code == 200
    assert resp.json()["default_page_size"] == 50


async def test_ui_config_is_clamped_to_a_sane_range(seeded_db_session):
    db = seeded_db_session
    actor = await _user(db)

    from sqlalchemy import select, update

    from app.models import SystemParameter
    from app.services.system_params import system_params

    # Out-of-range values must not hand the tables a nonsensical page size.
    await db.execute(
        update(SystemParameter)
        .where(SystemParameter.key == "pagination.default_page_size")
        .values(value=100000)
    )
    await db.flush()

    stored = (
        await db.execute(
            select(SystemParameter.value).where(
                SystemParameter.key == "pagination.default_page_size"
            )
        )
    ).scalar_one()
    assert stored == 100000
    # system_params keeps a process-level cache; drop it so the request re-reads.
    system_params.invalidate("pagination.default_page_size")

    async with _client(db) as client:
        resp = await client.get("/api/v1/ui-config", headers=_auth_headers(actor))

    assert resp.status_code == 200
    assert resp.json()["default_page_size"] == 200
