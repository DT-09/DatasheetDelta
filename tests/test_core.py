import csv
import io

import pytest

from datasheetdelta.core import compare, extract


def test_csv_extracts_fields_and_locations():
    data = b"Parameter,Value\nPressure,10 bar\nVoltage,24 V\n"
    fields, warnings = extract("x.csv", data)
    assert len(fields) == 2
    assert fields[0].source == "row 2"
    assert fields[0].dimension == "pressure"
    assert not warnings


def test_compare_changed_added_removed_and_unchanged():
    old, _ = extract("a.csv", b"Parameter,Value\nPressure,10 bar\nMaterial,Steel\n")
    new, _ = extract("b.csv", b"Parameter,Value\nPressure,12 bar\nVoltage,24 V\n")
    result = compare("a.csv", old, "b.csv", new)
    statuses = {item["parameter"]: item["status"] for item in result["findings"]}
    assert statuses == {"material": "removed", "pressure": "changed", "voltage": "added"}


def test_equivalent_units_compare_as_unchanged():
    old, _ = extract("a.csv", b"Parameter,Value\nLength,10 mm\n")
    new, _ = extract("b.csv", b"Parameter,Value\nLength,1 cm\n")
    result = compare("a.csv", old, "b.csv", new)
    assert result["findings"][0]["status"] == "unchanged"


def test_incompatible_units_are_not_compared_as_numbers():
    old, _ = extract("a.csv", b"Parameter,Value\nRating,10 bar\n")
    new, _ = extract("b.csv", b"Parameter,Value\nRating,10 V\n")
    result = compare("a.csv", old, "b.csv", new)
    assert result["findings"][0]["status"] == "unit_mismatch"


def test_duplicate_labels_are_preserved_and_flagged():
    data = b"Parameter,Value\nPressure,10 bar\nPressure,12 bar\n"
    fields, warnings = extract("x.csv", data)
    assert len(fields) == 2
    assert any("pressure" in warning for warning in warnings)
    result = compare("x.csv", fields, "y.csv", fields)
    assert result["findings"][0]["status"] == "ambiguous"


def test_text_extraction():
    fields, _ = extract("spec.txt", b"Material: Stainless steel\nVoltage: 24 V")
    assert {item.name for item in fields} == {"material", "voltage"}


def test_horizontal_key_value_pairs_are_extracted():
    fields, _ = extract("x.csv", b"Pressure,10 bar,Voltage,24 V\n")
    assert {item.name for item in fields} == {"pressure", "voltage"}


def test_negative_dimension_tolerance_rejected():
    with pytest.raises(ValueError):
        compare("a", [], "b", [], {"length": -0.1})


def test_report_csv_quotes_values_and_evidence():
    fields, _ = extract("x.csv", b'Parameter,Value\nMaterial,"Stainless, grade 316"\n')
    result = compare("x.csv", fields, "y.csv", fields)
    exported = csv.DictReader(io.StringIO(__import__("datasheetdelta.core", fromlist=["report_csv"]).report_csv(result)))
    row = next(exported)
    assert row["reference"] == "Stainless, grade 316"

def test_fahrenheit_and_celsius_are_normalized_with_offset():
    old, _ = extract("a.csv", "Parameter,Value\nTemperature,212 °F\n".encode("utf-8"))
    new, _ = extract("b.csv", "Parameter,Value\nTemperature,100 °C\n".encode("utf-8"))
    result = compare("a.csv", old, "b.csv", new)
    assert result["findings"][0]["status"] == "unchanged"


def test_same_unknown_unit_is_compared_without_conversion():
    old, _ = extract("a.csv", b"Parameter,Value\nCustom,10 furlongx\n")
    new, _ = extract("b.csv", b"Parameter,Value\nCustom,11 furlongx\n")
    result = compare("a.csv", old, "b.csv", new)
    assert result["findings"][0]["status"] == "changed"


def test_non_finite_dimension_tolerance_rejected():
    with pytest.raises(ValueError):
        compare("a", [], "b", [], {"length": float("nan")})


def test_csv_parameter_value_unit_columns_keep_the_unit():
    fields, _ = extract(
        "spec.csv",
        b"Parameter,Value,Unit\nPressure,10,bar\nLength,25,mm\n",
    )
    values = {item.name: item.value for item in fields}
    assert values == {"pressure": "10 bar", "length": "25 mm"}
    assert fields[0].dimension == "pressure"


def test_csv_export_neutralizes_spreadsheet_formulas():
    from datasheetdelta.core import _spreadsheet_safe
    assert _spreadsheet_safe("=HYPERLINK(\"https://example.invalid\")").startswith("'=")
    assert _spreadsheet_safe("@SUM(1,2)").startswith("'@")
    assert _spreadsheet_safe("normal text") == "normal text"


def test_scientific_notation_and_micrometre_conversion():
    scientific, _ = extract("a.csv", b"Parameter,Value\\nPower,1.2e3 W\\n")
    watts, _ = extract("b.csv", b"Parameter,Value\\nPower,1200 W\\n")
    assert compare("a.csv", scientific, "b.csv", watts)["findings"][0]["status"] == "unchanged"

    micrometres, _ = extract("c.csv", b"Parameter,Value\\nLength,1000 um\\n")
    millimetres, _ = extract("d.csv", b"Parameter,Value\\nLength,1 mm\\n")
    assert compare("c.csv", micrometres, "d.csv", millimetres)["findings"][0]["status"] == "unchanged"


def test_tolerance_only_applies_to_its_own_dimension():
    old, _ = extract("a.csv", b"Parameter,Value\\nLength,10 mm\\n")
    new, _ = extract("b.csv", b"Parameter,Value\\nLength,10.1 mm\\n")
    result = compare("a.csv", old, "b.csv", new, {"pressure": 1000})
    assert result["findings"][0]["status"] == "changed"
    result = compare("a.csv", old, "b.csv", new, {"length": 0.2})
    assert result["findings"][0]["status"] == "unchanged"


def test_non_finite_document_numeric_value_is_rejected():
    with pytest.raises(ValueError, match="outside the supported range"):
        extract("spec.csv", ("Parameter,Value\\nPressure," + ("9" * 500) + " bar\\n").encode())
