import pytest
from datasheetdelta.core import compare, extract

def fields(text, name="x.csv"):
    return extract(name, text.encode())[0]

def test_csv_extracts_fields_and_locations():
    extracted, warnings = extract("x.csv", b"Parameter,Value\nPressure,10 bar\nVoltage,24 V\n")
    assert len(extracted) == 2
    assert extracted[0].source == "row 2"
    assert not warnings

def test_equivalent_units_compare_equal_without_double_conversion():
    result = compare("old.csv", fields("Length,1 m"), "new.csv", fields("Length,100 cm"))
    assert result["findings"][0]["status"] == "unchanged"

def test_numeric_change_compares_in_base_units():
    result = compare("old.csv", fields("Pressure,10 bar"), "new.csv", fields("Pressure,12 bar"))
    assert result["findings"][0]["status"] == "changed"
    assert "Pa" in result["findings"][0]["explanation"]

def test_incompatible_dimensions_are_not_compared_as_numbers():
    result = compare("a.csv", fields("Rating,10 bar"), "b.csv", fields("Rating,10 V"))
    assert result["findings"][0]["status"] == "unit_mismatch"

def test_unknown_units_are_flagged():
    result = compare("a.csv", fields("Speed,10 rpm"), "b.csv", fields("Speed,12 Hz"))
    assert result["findings"][0]["status"] == "unit_mismatch"

def test_duplicate_labels_are_reported():
    extracted, warnings = extract("x.csv", b"Pressure,10 bar\nPressure,12 bar\n")
    assert len(extracted) == 1
    assert any("Duplicate field" in warning for warning in warnings)

def test_added_removed_and_unchanged_summary():
    result = compare("a.csv", fields("Pressure,10 bar\nMaterial,Steel"),
                     "b.csv", fields("Pressure,10 bar\nVoltage,24 V"))
    assert {item["parameter"]: item["status"] for item in result["findings"]} == {
        "material": "removed", "pressure": "unchanged", "voltage": "added"}
    assert result["summary"]["total"] == 3
    assert result["summary"]["review_required"] is True

def test_negative_or_non_finite_tolerance_rejected():
    with pytest.raises(ValueError):
        compare("a", [], "b", [], -1)
    with pytest.raises(ValueError):
        compare("a", [], "b", [], float("nan"))

def test_text_extraction():
    extracted, _ = extract("spec.txt", b"Material: Stainless steel\nVoltage: 24 V")
    assert {item.name for item in extracted} == {"material", "voltage"}
