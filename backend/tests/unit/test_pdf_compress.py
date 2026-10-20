"""Compression must never be the reason an upload fails."""

from __future__ import annotations

import pytest

from app.services import pdf_compress

# A tiny, structurally valid-enough PDF: the point is that compression is a
# no-op on files it cannot improve, not that ghostscript handles this example.
TINY_PDF = b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 200]>>endobj
trailer<</Root 1 0 R>>
%%EOF
"""


async def test_non_pdf_content_is_returned_untouched(seeded_db_session):
    payload = b"not a pdf at all"

    result = await pdf_compress.compress_pdf_if_worthwhile(seeded_db_session, payload, "image/png")

    assert result is payload


async def test_non_pdf_mime_is_skipped_even_with_pdf_magic(seeded_db_session):
    result = await pdf_compress.compress_pdf_if_worthwhile(
        seeded_db_session, TINY_PDF, "text/plain"
    )

    assert result is TINY_PDF


@pytest.mark.parametrize("payload", [TINY_PDF, b"%PDF-1.4\ntruncated"])
async def test_failure_keeps_the_original_bytes(seeded_db_session, payload):
    """Whatever ghostscript makes of it, the caller gets usable bytes back."""
    result = await pdf_compress.compress_pdf_if_worthwhile(
        seeded_db_session, payload, "application/pdf"
    )

    assert isinstance(result, bytes)
    assert result.startswith(b"%PDF")
