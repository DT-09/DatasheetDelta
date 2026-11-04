from datasheetdelta.core import compare, extract


def test_missing_unit_is_flagged_for_review():
    old, _ = extract("old.csv", b"Pressure,10 bar\n")
    new, _ = extract("new.csv", b"Pressure,10\n")
    result = compare("old.csv", old, "new.csv", new)
    assert result["findings"][0]["status"] == "unit_mismatch"


def test_unitless_numeric_tolerance_is_applied():
    old, _ = extract("old.csv", b"Revision,1.0\n")
    new, _ = extract("new.csv", b"Revision,1.005\n")
    result = compare("old.csv", old, "new.csv", new, tolerance=0.01)
    assert result["findings"][0]["status"] == "unchanged"
