from datasheetdelta.core import extract


def test_range_table_creates_minimum_and_maximum_fields():
    data = b"Parameter,Min,Max,Unit\nPressure,0,10,bar\n"
    fields, warnings = extract("range.csv", data)
    values = {item.name: item.value for item in fields}
    assert values == {"pressure_min": "0 bar", "pressure_max": "10 bar"}
    assert all(item.source == "row 2" for item in fields)
    assert warnings == []


def test_value_and_unit_columns_are_combined():
    data = b"Parameter,Value,Unit\nRated voltage,24,V\n"
    fields, _ = extract("electrical.csv", data)
    assert fields[0].name == "rated_voltage"
    assert fields[0].value == "24 V"
