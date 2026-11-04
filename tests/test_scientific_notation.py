from decimal import Decimal

from datasheetdelta.core import compare, extract


def test_scientific_notation_is_parsed_and_compared():
    old, _ = extract("old.csv", b"Capacitance,1.2e3 pF\n")
    new, _ = extract("new.csv", b"Capacitance,1200 pF\n")
    assert old[0].number == Decimal("1.2e-9")
    result = compare("old.csv", old, "new.csv", new)
    assert result["findings"][0]["status"] == "unchanged"
