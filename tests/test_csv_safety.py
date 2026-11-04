from datasheetdelta.core import report_csv


def test_csv_report_neutralizes_formula_cells_but_keeps_negative_values():
    report = {
        "findings": [{
            "parameter": "=HYPERLINK(1,2)",
            "status": "changed",
            "reference": "-10 °C",
            "revised": "-cmd|' /C calc'!A0",
            "reference_source": "row 2",
            "revised_source": "row 2",
            "reference_excerpt": "+SUM(1,2)",
            "revised_excerpt": "@SUM(1,2)",
            "explanation": "Value differs",
        }]
    }
    output = report_csv(report)
    assert "'=HYPERLINK" in output
    assert "-10 °C" in output
    assert "'-cmd" in output
    assert "'+SUM" in output
    assert "'@SUM" in output
