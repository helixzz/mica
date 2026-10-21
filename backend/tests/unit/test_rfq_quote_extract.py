"""Reading a scanned quotation must stay a preview and must say what it skipped."""

import io

import pytest
from sqlalchemy import select

from app.db import new_uuid
from app.models import AIFeatureRouting, User
from app.services import rfq_quote_extract as svc


def _pdf(pages: int) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    pdf = canvas.Canvas(buf, pagesize=A4)
    for index in range(pages):
        pdf.drawString(72, 720, f"quotation page {index + 1}")
        pdf.showPage()
    pdf.save()
    return buf.getvalue()


async def _actor(db) -> User:
    return (await db.execute(select(User).where(User.username == "alice"))).scalar_one()


@pytest.fixture
async def routed(db_session):
    """A route row is enough; the model call itself is stubbed per test."""
    row = AIFeatureRouting(
        feature_code=svc.FEATURE_CODE,
        primary_model_id=None,
        fallback_model_ids=[],
        temperature=0.1,
        max_tokens=2000,
        enabled=True,
    )
    db_session.add(row)
    await db_session.commit()
    return row


def _page_payload(**overrides) -> dict:
    payload = {
        "supplier_name": "测试供应商",
        "currency": "CNY",
        "valid_until": None,
        "confidence": 0.8,
        "lines": [
            {
                "line_no": 1,
                "item_name": "服务器",
                "specification": "2U",
                "qty": 2,
                "unit_price": 1000,
                "tax_rate": 0.13,
                "delivery_days": 7,
                "confidence": 0.9,
                "line_total": 2000,
            }
        ],
    }
    payload.update(overrides)
    return payload


@pytest.mark.asyncio
async def test_image_extraction_returns_a_preview(seeded_db_session, routed, monkeypatch):
    db = seeded_db_session
    actor = await _actor(db)

    async def fake_read(db_, actor_, image, content_type):
        return _page_payload()

    monkeypatch.setattr(svc, "_read_page", fake_read)

    result = await svc.extract_rfq_quote(db, actor, b"\xff\xd8\xff", "image/jpeg", "scan.jpg")

    assert result["error"] is None
    assert result["supplier_name"] == "测试供应商"
    assert len(result["lines"]) == 1
    assert result["lines"][0]["unit_price"] == 2000 / 2  # sanity: parsed as a number
    assert result["warnings"] == []


@pytest.mark.asyncio
async def test_a_wrong_line_total_is_reported(seeded_db_session, routed, monkeypatch):
    """The form promises qty × price = total; catch the model contradicting it."""
    db = seeded_db_session
    actor = await _actor(db)

    async def fake_read(db_, actor_, image, content_type):
        payload = _page_payload()
        payload["lines"][0]["line_total"] = 1500  # 2 × 1000 should be 2000
        return payload

    monkeypatch.setattr(svc, "_read_page", fake_read)

    result = await svc.extract_rfq_quote(db, actor, b"\xff\xd8\xff", "image/jpeg", "scan.jpg")

    assert any("line 1" in warning for warning in result["warnings"])


@pytest.mark.asyncio
async def test_pdf_reads_every_page_and_merges_rows(seeded_db_session, routed, monkeypatch):
    db = seeded_db_session
    actor = await _actor(db)
    seen: list[int] = []

    async def fake_read(db_, actor_, image, content_type):
        seen.append(len(seen) + 1)
        second = len(seen) == 2
        return _page_payload(
            lines=[
                {
                    "line_no": 2 if second else 1,
                    "item_name": "光模块" if second else "服务器",
                    "qty": 1,
                    "unit_price": 100,
                    "tax_rate": 0.13,
                    "confidence": 0.7,
                }
            ]
        )

    monkeypatch.setattr(svc, "_read_page", fake_read)

    result = await svc.extract_rfq_quote(db, actor, _pdf(2), "application/pdf", "scan.pdf")

    assert result["error"] is None
    assert seen == [1, 2]
    assert len(result["lines"]) == 2
    assert result["pages_read"] == 2
    assert result["pages_total"] == 2


@pytest.mark.asyncio
async def test_pages_beyond_the_limit_are_announced(seeded_db_session, routed, monkeypatch):
    """Silently dropping a page is the failure mode that matters most."""
    db = seeded_db_session
    actor = await _actor(db)

    async def fake_read(db_, actor_, image, content_type):
        return _page_payload()

    monkeypatch.setattr(svc, "_read_page", fake_read)
    from app.services.system_params import system_params

    async def fake_get_int_or(db_, key, default):
        return 1 if "pages" in key else default

    monkeypatch.setattr(system_params, "get_int_or", fake_get_int_or)

    result = await svc.extract_rfq_quote(db, actor, _pdf(3), "application/pdf", "scan.pdf")

    assert result["error"] is None, result["error"]
    assert result["pages_read"] == 1
    assert result["pages_total"] == 3
    assert any("only the first" in warning for warning in result["warnings"])


@pytest.mark.asyncio
async def test_non_json_reply_becomes_an_error_not_a_crash(seeded_db_session, routed, monkeypatch):
    db = seeded_db_session
    actor = await _actor(db)

    async def fake_read(db_, actor_, image, content_type):
        raise RuntimeError("vision_returned_non_json")

    monkeypatch.setattr(svc, "_read_page", fake_read)

    result = await svc.extract_rfq_quote(db, actor, b"\xff\xd8\xff", "image/jpeg", "scan.jpg")

    assert result["error"] == "vision_returned_non_json"
    assert result["lines"] == []


@pytest.mark.asyncio
async def test_json_is_parsed_out_of_a_fenced_block():
    raw = '```json\n{"lines": [], "confidence": 0.5}\n```'

    assert svc._parse_json(raw)["confidence"] == 0.5


@pytest.mark.asyncio
async def test_unsupported_content_type_is_reported(seeded_db_session, routed):
    db = seeded_db_session
    actor = await _actor(db)

    result = await svc.extract_rfq_quote(db, actor, b"xlsx-bytes", "application/vnd.ms-excel")

    assert result["error"] and "unsupported_content_type" in result["error"]


async def test_call_log_names_the_model_that_read_the_scan(seeded_db_session, monkeypatch):
    """A log that says model_name=None cannot answer 'which model got this wrong'."""
    db = seeded_db_session
    actor = await _actor(db)

    from app.models import AICallLog, AIModel

    model_row = AIModel(
        id=new_uuid(),
        name="attribution-model",
        provider="openai",
        model_string="test/attribution",
        modality="vision",
        is_active=True,
    )
    db.add(model_row)
    await db.flush()
    # The route has to live in the same session the service reads it from; the
    # `routed` fixture belongs to another session and its edit is invisible here.
    db.add(
        AIFeatureRouting(
            feature_code=svc.FEATURE_CODE,
            primary_model_id=model_row.id,
            fallback_model_ids=[],
            temperature=0.1,
            max_tokens=2000,
            enabled=True,
        )
    )
    await db.commit()

    async def fake_read(db_, actor_, image, content_type):
        return _page_payload()

    monkeypatch.setattr(svc, "_read_page", fake_read)

    await svc.extract_rfq_quote(db, actor, b"\xff\xd8\xff", "image/jpeg", "scan.jpg")

    log = (
        (
            await db.execute(
                select(AICallLog)
                .where(AICallLog.feature_code == svc.FEATURE_CODE)
                .order_by(AICallLog.occurred_at.desc())
            )
        )
        .scalars()
        .first()
    )

    assert log is not None
    assert log.model_name == "attribution-model"
    assert log.provider == "openai"
