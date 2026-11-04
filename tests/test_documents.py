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


def test_docx_three_column_table_keeps_units():
    document = Document()
    table = document.add_table(rows=2, cols=3)
    for column, value in enumerate(["Parameter", "Value", "Unit"]):
        table.cell(0, column).text = value
    for column, value in enumerate(["Pressure", "10", "bar"]):
        table.cell(1, column).text = value
    buffer = BytesIO()
    document.save(buffer)

    fields, _ = extract("spec.docx", buffer.getvalue())
    assert len(fields) == 1
    assert fields[0].value == "10 bar"
    assert fields[0].dimension == "pressure"


def test_office_archive_expansion_limit_rejects_zip_bomb():
    from zipfile import ZIP_DEFLATED, ZipFile
    import pytest
    from datasheetdelta.core import _validate_office_archive

    buffer = BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("xl/workbook.xml", "A" * 5_000_000)
    with pytest.raises(ValueError, match="compression ratio"):
        _validate_office_archive(buffer.getvalue(), "xl/workbook.xml")
