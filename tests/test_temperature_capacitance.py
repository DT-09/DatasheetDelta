from datasheetdelta.core import compare, extract


def test_farads_are_interpreted_as_capacitance_for_capacitance_field():
    old, _ = extract("old.csv", b"Capacitance,1 uF\n")
    new, _ = extract("new.csv", b"Capacitance,1000 nF\n")
    result = compare("old.csv", old, "new.csv", new, tolerance=1e-12)
    assert result["findings"][0]["status"] == "unchanged"


def test_kelvin_and_celsius_are_comparable():
    old, _ = extract("old.csv", b"Temperature,273.15 K\n")
    new, _ = extract("new.csv", b"Temperature,0 C\n")
    result = compare("old.csv", old, "new.csv", new, tolerance=1e-9)
    assert result["findings"][0]["status"] == "unchanged"
