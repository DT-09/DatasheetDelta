from io import BytesIO

import openpyxl
from docx import Document
from reportlab.pdfgen import canvas

from datasheetdelta.core import extract


def test_xlsx_extracts_multiple_sheets_with_locations():
    workbook = openpyxl.Workbook()
    first = workbook.active
    first.title = "Electrical"
    first.append(["Parameter", "Value"])
    first.append(["Voltage", "24 V"])
    second = workbook.create_sheet("Mechanical")
    second.append(["Parameter", "Value"])
    second.append(["Diameter", "12 mm"])
    buffer = BytesIO()
    workbook.save(buffer)

    fields, warnings = extract("spec.xlsx", buffer.getvalue())
    sources = {item.name: item.source for item in fields}
    assert sources == {"voltage": "Electrical!row 2", "diameter": "Mechanical!row 2"}
    assert warnings == []


def test_docx_extracts_table_and_paragraph_locations():
    document = Document()
    table = document.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "Parameter"
    table.cell(0, 1).text = "Value"
    table.cell(1, 0).text = "Pressure"
    table.cell(1, 1).text = "5 bar"
    document.add_paragraph("Material: Stainless steel")
    buffer = BytesIO()
    document.save(buffer)

    fields, _ = extract("spec.docx", buffer.getvalue())
    sources = {item.name: item.source for item in fields}
    assert sources["pressure"] == "table 1, row 2"
    assert sources["material"] == "paragraph 1"


def test_text_pdf_extracts_page_and_line_locations():
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer)
    pdf.drawString(72, 750, "Pressure: 5 bar")
    pdf.save()

    fields, warnings = extract("spec.pdf", buffer.getvalue())
    assert fields[0].name == "pressure"
    assert fields[0].source == "page 1, line 1"
    assert warnings == []


def test_file_signature_must_match_document_extension():
    for filename, data, expected in [
        ("fake.pdf", b"not a PDF document", "not a PDF"),
        ("fake.docx", b"not a ZIP package", "Office Open XML"),
    ]:
        try:
            extract(filename, data)
        except ValueError as error:
            assert expected in str(error)
        else:
            raise AssertionError("Mismatched document signature must be rejected")
