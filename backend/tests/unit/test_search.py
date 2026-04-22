# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportExplicitAny=false

from typing import Any, cast

from sqlalchemy import select

from app.models import User
from app.services import search as svc


async def _get_user(seeded_db_session, username: str) -> User:
    return (
        await seeded_db_session.execute(select(User).where(User.username == username))
    ).scalar_one()


async def _allow_all_meta(data, **_kwargs):
    return data


async def test_unified_search_matches_seeded_dell_data(seeded_db_session, monkeypatch):
    monkeypatch.setattr(svc, "filter_dict_via_cerbos", _allow_all_meta)
    actor = await _get_user(seeded_db_session, "admin")

    result = cast(
        dict[str, Any],
        await svc.unified_search(seeded_db_session, actor=actor, query="Dell"),
    )
    by_type = cast(dict[str, list[dict[str, Any]]], result["by_type"])
    top_hits = cast(list[dict[str, Any]], result["top_hits"])

    assert result["total"] >= 2
    assert any("Dell" in hit["title"] for hit in by_type["supplier"])
    assert any("Dell" in hit["title"] for hit in by_type["item"])
    assert {hit["entity_type"] for hit in top_hits} >= {"supplier", "item"}


async def test_unified_search_empty_query_returns_empty_payload(seeded_db_session):
    actor = await _get_user(seeded_db_session, "admin")

    result = await svc.unified_search(seeded_db_session, actor=actor, query="   ")

    assert result == {"total": 0, "by_type": {}, "top_hits": []}


async def test_unified_search_respects_requested_entity_types(seeded_db_session):
    actor = await _get_user(seeded_db_session, "admin")

    result = cast(
        dict[str, Any],
        await svc.unified_search(
            seeded_db_session,
            actor=actor,
            query="Dell",
            entity_types=["supplier"],
        ),
    )
    by_type = cast(dict[str, list[dict[str, Any]]], result["by_type"])
    top_hits = cast(list[dict[str, Any]], result["top_hits"])

    assert set(by_type.keys()) == {"supplier"}
    assert result["total"] == len(by_type["supplier"])
    assert result["total"] >= 1
    assert all(hit["entity_type"] == "supplier" for hit in top_hits)
