from datasheetdelta.core import compare, extract

def by_name(fields):
    return {field.name: field for field in fields}

def test_csv_extracts_fields_and_locations():
    fields, warnings = extract("x.csv", b"Parameter,Value\nPressure,10 bar\nVoltage,24 V\n")
    assert len(fields) == 2
    assert fields[0].source == "row 2"
    assert warnings == []

def test_compare_changed_added_removed_unchanged():
    old, _ = extract("a.csv", b"Parameter,Value\nPressure,10 bar\nMaterial,Steel\n")
    new, _ = extract("b.csv", b"Parameter,Value\nPressure,12 bar\nVoltage,24 V\n")
    result = compare("a.csv", old, "b.csv", new)
    statuses = {item["parameter"]: item["status"] for item in result["findings"]}
    assert statuses == {"material": "removed", "pressure": "changed", "voltage": "added"}

def test_unit_normalization_handles_equivalent_pressure():
    old, _ = extract("a.csv", b"Pressure,1 bar\n")
    new, _ = extract("b.csv", b"Pressure,100 kPa\n")
    result = compare("a.csv", old, "b.csv", new)
    assert result["findings"][0]["status"] == "unchanged"

def test_unit_normalization_handles_fahrenheit_and_celsius():
    old, _ = extract("a.csv", b"Temperature,212 F\n")
    new, _ = extract("b.csv", b"Temperature,100 C\n")
    result = compare("a.csv", old, "b.csv", new, tolerance=0.000001)
    assert result["findings"][0]["status"] == "unchanged"

def test_duplicate_labels_are_preserved_and_flagged():
    fields, warnings = extract("a.csv", b"Parameter,Value\nPressure,10 bar\nPressure,12 bar\n")
    assert len(fields) == 2
    assert any("Repeated parameter labels" in warning for warning in warnings)
    result = compare("a.csv", fields, "b.csv", fields)
    assert result["findings"][0]["status"] == "ambiguous"

def test_text_supports_colon_equals_and_aligned_columns():
    fields, _ = extract("spec.txt", b"Material: Stainless steel\nVoltage = 24 V\nCurrent    2 A\n")
    assert {item.name for item in fields} == {"material", "voltage", "current"}

def test_unknown_and_dimensionally_incompatible_units_are_not_silently_converted():
    old, _ = extract("a.csv", b"Pressure,10 bar\n")
    new, _ = extract("b.csv", b"Pressure,10 V\n")
    result = compare("a.csv", old, "b.csv", new)
    assert result["findings"][0]["status"] == "unit_mismatch"

def test_tolerance_must_be_non_negative():
    fields, _ = extract("a.csv", b"Pressure,10 bar\n")
    try:
        compare("a.csv", fields, "b.csv", fields, tolerance=-1)
    except ValueError as exc:
        assert "non-negative" in str(exc)
    else:
        raise AssertionError("Negative tolerance must fail")

def test_empty_document_rejected():
    try:
        extract("empty.csv", b"")
    except ValueError as exc:
        assert "empty" in str(exc).lower()
    else:
        raise AssertionError("Empty document must fail")

def test_aliases_are_canonicalized():
    fields, _ = extract("a.csv", b"Maximum Pressure,10 bar\n")
    assert fields[0].name == "maximum_pressure"
