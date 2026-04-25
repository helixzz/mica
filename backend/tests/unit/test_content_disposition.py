from app.api.v1.document_templates import _content_disposition


def test_content_disposition_ascii_filename_is_latin1_safe():
    header = _content_disposition("payment_form_2026.xlsx")
    header.encode("latin-1")
    assert 'filename="payment_form_2026.xlsx"' in header
    assert "filename*=UTF-8''payment_form_2026.xlsx" in header


def test_content_disposition_chinese_filename_is_latin1_safe():
    filename = "AcmeProcure_供应商全名_货款_HT-2026-001_500000.00_20260425.xlsx"
    header = _content_disposition(filename)

    header.encode("latin-1")

    assert "filename*=UTF-8''" in header
    assert "%E4%BD%B3%E6%9C%9F" in header
    assert 'filename="' in header


def test_content_disposition_pure_non_ascii_keeps_safe_fallback():
    header = _content_disposition("付款表.xlsx")

    header.encode("latin-1")

    assert 'filename="download"' in header or 'filename=".xlsx"' in header
    assert "filename*=UTF-8''%E4%BB%98%E6%AC%BE%E8%A1%A8.xlsx" in header
