import json

from datasheetdelta.cli import main


def test_cli_writes_json_csv_and_pdf_reports(tmp_path, monkeypatch):
    reference = tmp_path / "reference.csv"
    revised = tmp_path / "revised.csv"
    reference.write_text("Parameter,Value\nPressure,1 bar\n", encoding="utf-8")
    revised.write_text("Parameter,Value\nPressure,2 bar\n", encoding="utf-8")
    prefix = tmp_path / "out" / "comparison"
    monkeypatch.setattr(
        "sys.argv",
        ["datasheetdelta", str(reference), str(revised), "--out", str(prefix)],
    )

    assert main() == 0
    json_report = prefix.with_suffix(".json")
    csv_report = prefix.with_suffix(".csv")
    pdf_report = prefix.with_suffix(".pdf")
    assert json.loads(json_report.read_text(encoding="utf-8"))["findings"][0]["status"] == "changed"
    assert "reference_excerpt" in csv_report.read_text(encoding="utf-8-sig")
    assert pdf_report.read_bytes().startswith(b"%PDF-")
