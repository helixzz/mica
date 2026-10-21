"""The routing table can point at a disabled model, and its fallbacks used to be
written by the admin UI but never read — a failover setting that did nothing."""

import pytest

from app.db import new_uuid
from app.models import AIFeatureRouting, AIModel
from app.services.ai import _get_routing


async def _model(db, name: str, *, active: bool) -> AIModel:
    row = AIModel(
        id=new_uuid(),
        name=name,
        provider="openai",
        model_string=f"test/{name}",
        modality="vision",
        is_active=active,
    )
    db.add(row)
    await db.flush()
    return row


async def _routing(db, *, primary, fallbacks: list[str] | None = None) -> AIFeatureRouting:
    row = AIFeatureRouting(
        id=new_uuid(),
        feature_code="test_vision_route",
        primary_model_id=primary,
        fallback_model_ids=fallbacks,
        enabled=True,
    )
    db.add(row)
    await db.flush()
    return row


@pytest.mark.asyncio
async def test_routing_ignores_a_disabled_primary(seeded_db_session):
    db = seeded_db_session
    dead = await _model(db, "route-dead", active=False)
    alive = await _model(db, "route-alive", active=True)
    await _routing(db, primary=dead.id, fallbacks=[str(alive.id)])
    await db.commit()

    _, model = await _get_routing(db, "test_vision_route")

    assert model is not None
    assert model.id == alive.id


@pytest.mark.asyncio
async def test_routing_returns_none_when_every_model_is_disabled(seeded_db_session):
    db = seeded_db_session
    dead = await _model(db, "route-dead-2", active=False)
    also_dead = await _model(db, "route-dead-3", active=False)
    await _routing(db, primary=dead.id, fallbacks=[str(also_dead.id)])
    await db.commit()

    _, model = await _get_routing(db, "test_vision_route")

    assert model is None


@pytest.mark.asyncio
async def test_routing_survives_a_malformed_fallback_id(seeded_db_session):
    """The column is JSONB text; a hand-edited value must not crash the request."""
    db = seeded_db_session
    alive = await _model(db, "route-alive-2", active=True)
    await _routing(db, primary=None, fallbacks=["not-a-uuid", str(alive.id)])
    await db.commit()

    _, model = await _get_routing(db, "test_vision_route")

    assert model is not None
    assert model.id == alive.id


@pytest.mark.asyncio
async def test_routing_rejects_a_disabled_feature(seeded_db_session):
    db = seeded_db_session
    alive = await _model(db, "route-alive-3", active=True)
    row = await _routing(db, primary=alive.id)
    row.enabled = False
    await db.commit()

    with pytest.raises(RuntimeError, match=r"ai\.feature_disabled"):
        await _get_routing(db, "test_vision_route")


async def test_routing_skips_a_model_of_the_wrong_kind(seeded_db_session):
    """A vision feature routed at a text model fails at request time with an error
    that names the provider, not the actual mistake."""
    db = seeded_db_session
    text_model = AIModel(
        id=new_uuid(),
        name="route-text-only",
        provider="openai",
        model_string="test/text-only",
        modality="text",
        is_active=True,
    )
    db.add(text_model)
    await db.flush()
    vision_model = await _model(db, "route-vision", active=True)
    await _routing(db, primary=text_model.id, fallbacks=[str(vision_model.id)])
    await db.commit()

    _, model = await _get_routing(db, "test_vision_route", required_modality="vision")

    assert model is not None
    assert model.id == vision_model.id


async def test_routing_returns_none_when_no_model_matches_the_modality(seeded_db_session):
    db = seeded_db_session
    text_model = AIModel(
        id=new_uuid(),
        name="route-text-only-2",
        provider="openai",
        model_string="test/text-only-2",
        modality="text",
        is_active=True,
    )
    db.add(text_model)
    await db.flush()
    await _routing(db, primary=text_model.id)
    await db.commit()

    _, model = await _get_routing(db, "test_vision_route", required_modality="vision")

    assert model is None
