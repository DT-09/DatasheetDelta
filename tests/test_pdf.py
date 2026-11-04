from io import BytesIO

from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from datasheetdelta.core import extract


def make_text_pdf(text: str) -> bytes:
    writer = PdfWriter()
    page = writer.add_blank_page(width=300, height=300)
    font = DictionaryObject({
        NameObject("/Type"): NameObject("/Font"),
        NameObject("/Subtype"): NameObject("/Type1"),
        NameObject("/BaseFont"): NameObject("/Helvetica"),
    })
    font_ref = writer._add_object(font)
    font_resources = DictionaryObject({NameObject("/F1"): font_ref})
    resources = DictionaryObject({NameObject("/Font"): font_resources})
    page[NameObject("/Resources")] = resources
    stream = DecodedStreamObject()
    stream.set_data(f"BT /F1 12 Tf 10 100 Td ({text}) Tj ET".encode("ascii"))
    page[NameObject("/Contents")] = writer._add_object(stream)
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def test_text_pdf_extraction_preserves_page_and_line_provenance():
    fields, warnings = extract("spec.pdf", make_text_pdf("Pressure: 10 bar"))
    assert len(fields) == 1
    assert fields[0].name == "pressure"
    assert fields[0].value == "10 bar"
    assert fields[0].source == "page 1, line 1"
    assert not warnings


def test_pdf_without_extractable_text_warns_that_ocr_is_not_available():
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=300)
    buffer = BytesIO()
    writer.write(buffer)
    fields, warnings = extract("scan.pdf", buffer.getvalue())
    assert not fields
    assert any("OCR is not included" in warning for warning in warnings)
