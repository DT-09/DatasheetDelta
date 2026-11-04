from io import BytesIO

from docx import Document
from openpyxl import Workbook

from datasheetdelta.core import extract


def test_xlsx_extraction_preserves_sheet_and_row_location():
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Electrical"
    sheet.append(["Parameter", "Value"])
    sheet.append(["Rated voltage", "24 V"])
    buffer = BytesIO()
    workbook.save(buffer)

    fields, warnings = extract("spec.xlsx", buffer.getvalue())
    assert len(fields) == 1
    assert fields[0].name == "rated_voltage"
    assert fields[0].source == "Electrical! row 2"
    assert not warnings


def test_docx_table_extraction_preserves_table_and_row_location():
    document = Document()
    table = document.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "Parameter"
    table.cell(0, 1).text = "Value"
    table.cell(1, 0).text = "Material"
    table.cell(1, 1).text = "Stainless steel"
    buffer = BytesIO()
    document.save(buffer)

    fields, warnings = extract("spec.docx", buffer.getvalue())
    assert len(fields) == 1
    assert fields[0].name == "material"
    assert fields[0].value == "Stainless steel"
    assert fields[0].source == "table 1, row 2"
    assert not warnings
