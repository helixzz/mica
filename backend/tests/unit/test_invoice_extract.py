# pyright: reportPrivateUsage=false
import io
import zipfile

from app.services.invoice_extract import (
    ExtractSource,
    _extract_ofd,
    _extract_xml,
    _is_zip,
    _looks_xml,
    _regex_extract,
)


def test_looks_xml_with_declaration():
    assert _looks_xml(b'<?xml version="1.0"?><root/>') is True


def test_looks_xml_with_tag():
    assert _looks_xml(b"<Invoice></Invoice>") is True


def test_looks_xml_with_leading_whitespace():
    assert _looks_xml(b"   \n  <root/>") is True


def test_looks_xml_false_for_plain_text():
    assert _looks_xml(b"hello world") is False


def test_looks_xml_false_for_pdf():
    assert _looks_xml(b"%PDF-1.7") is False


def test_is_zip_true():
    assert _is_zip(b"PK\x03\x04rest") is True


def test_is_zip_false():
    assert _is_zip(b"%PDF") is False


def test_extract_xml_standard_tags():
    xml = b"""<?xml version="1.0" encoding="UTF-8"?>
    <Invoice>
        <InvoiceNumber>12345678</InvoiceNumber>
        <InvoiceCode>3200001</InvoiceCode>
        <IssueDate>2026-05-20</IssueDate>
        <SellerName>Acme Corp</SellerName>
        <SellerTaxID>91320000ABC</SellerTaxID>
        <BuyerName>Mica Inc</BuyerName>
        <BuyerTaxID>91440000XYZ</BuyerTaxID>
        <TaxExclusiveAmount>1000.00</TaxExclusiveAmount>
        <TaxAmount>130.00</TaxAmount>
        <TaxInclusiveAmount>1130.00</TaxInclusiveAmount>
    </Invoice>"""
    result = _extract_xml(xml)
    assert result.invoice_number == "12345678"
    assert result.invoice_code == "3200001"
    assert result.invoice_date == "2026-05-20"
    assert result.seller_name == "Acme Corp"
    assert result.seller_tax_id == "91320000ABC"
    assert result.buyer_name == "Mica Inc"
    assert result.subtotal == "1000.00"
    assert result.tax_amount == "130.00"
    assert result.total_amount == "1130.00"
    assert result.raw_extract_source == ExtractSource.XML.value
    assert result.confidence == 0.99


def test_extract_xml_alternative_tags():
    xml = b"""<?xml version="1.0"?>
    <invoice>
        <invoiceNo>87654321</invoiceNo>
        <salerName>Vendor Ltd</salerName>
        <amountWithTax>500.00</amountWithTax>
    </invoice>"""
    result = _extract_xml(xml)
    assert result.invoice_number == "87654321"
    assert result.seller_name == "Vendor Ltd"
    assert result.total_amount == "500.00"


def test_extract_xml_parse_error():
    result = _extract_xml(b"<not valid xml <<<")
    assert result.error is not None
    assert "xml_parse_error" in result.error
    assert result.raw_extract_source == ExtractSource.XML.value


def test_extract_xml_missing_fields_returns_none():
    xml = b"<?xml version='1.0'?><Invoice><InvoiceNumber>999</InvoiceNumber></Invoice>"
    result = _extract_xml(xml)
    assert result.invoice_number == "999"
    assert result.seller_name is None
    assert result.total_amount is None


def test_regex_extract_chinese_invoice_text():
    text = (
        "发票号码：12345678901234567890\n"
        "开票日期：2026年05月20日\n"
        "价税合计（小写）¥1,130.00\n"
        "合计金额 ¥1,000.00\n"
        "合计税额：¥130.00\n"
    )
    result = _regex_extract(text, ExtractSource.PDF_TEXT)
    assert result.invoice_number == "12345678901234567890"
    assert result.total_amount == "1130.00"
    assert result.confidence > 0


def test_regex_extract_no_match_low_confidence():
    result = _regex_extract("random unrelated text", ExtractSource.PDF_TEXT)
    assert result.confidence == 0.0
    assert result.invoice_number is None


def test_regex_extract_date_normalization():
    text = "开票日期：2026年05月20日"
    result = _regex_extract(text, ExtractSource.OFD)
    assert result.invoice_date == "2026-05-20"


def test_extract_ofd_with_embedded_xml():
    inner_xml = (
        b"<?xml version='1.0'?><Invoice>"
        b"<InvoiceNumber>OFD123456</InvoiceNumber>"
        b"<TaxInclusiveAmount>2000.00</TaxInclusiveAmount>"
        b"</Invoice>"
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("invoice.xml", inner_xml)
    result = _extract_ofd(buf.getvalue())
    assert result.invoice_number == "OFD123456"
    assert result.raw_extract_source == ExtractSource.OFD.value


def test_extract_ofd_corrupt_zip():
    result = _extract_ofd(b"not a real zip file")
    assert result.error is not None
    assert "ofd_parse_error" in result.error
