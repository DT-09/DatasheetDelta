from fastapi.testclient import TestClient

from datasheetdelta.api import app

client = TestClient(app)

def test_api_rejects_invalid_tolerance_profile():
    reference = ("reference.csv", b"Parameter,Value\nPressure,10 bar\n", "text/csv")
    revised = ("revised.csv", b"Parameter,Value\nPressure,12 bar\n", "text/csv")
    response = client.post(
        "/api/investigations",
        files={"reference": reference, "revised": revised},
        data={"tolerances": '{"length": -1}'},
    )
    assert response.status_code == 422
