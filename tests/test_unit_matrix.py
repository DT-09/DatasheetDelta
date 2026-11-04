import pytest

from datasheetdelta.core import compare, extract


@pytest.mark.parametrize(
    ("reference", "revised"),
    [
        ("1 m", "100 cm"),
        ("1 bar", "100 kPa"),
        ("1 kV", "1000 V"),
        ("1 A", "1000 mA"),
        ("1 kW", "1000 W"),
        ("1 MHz", "1000 kHz"),
        ("1 kg", "1000 g"),
        ("1 uF", "1000 nF"),
        ("0 C", "32 F"),
        ("1 rpm", "1 rpm"),
    ],
)
def test_advertised_unit_pairs_normalize_consistently(reference, revised):
    old, _ = extract("old.csv", f"Value,{reference}\n".encode())
    new, _ = extract("new.csv", f"Value,{revised}\n".encode())
    result = compare("old.csv", old, "new.csv", new, tolerance=1e-7)
    assert result["findings"][0]["status"] == "unchanged"
