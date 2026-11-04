from fastapi.testclient import TestClient

from datasheetdelta.api import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_investigation_endpoint_returns_source_linked_findings():
    reference = ("reference.csv", b"Parameter,Value\nPressure,10 bar\n", "text/csv")
    revised = ("revised.csv", b"Parameter,Value\nPressure,12 bar\n", "text/csv")
    response = client.post(
        "/api/investigations",
        files={"reference": reference, "revised": revised},
        data={"tolerance": "0"},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["findings"][0]["status"] == "changed"
    assert result["findings"][0]["reference_source"].startswith("row 2 [")


def test_unsupported_extension_is_rejected():
    reference = ("reference.exe", b"not a document", "application/octet-stream")
    revised = ("revised.csv", b"Parameter,Value\nPressure,10 bar\n", "text/csv")
    response = client.post(
        "/api/investigations",
        files={"reference": reference, "revised": revised},
    )
    assert response.status_code == 415


def test_export_endpoint_returns_csv_attachment():
    reference = ("reference.csv", b"Parameter,Value\nPressure,10 bar\n", "text/csv")
    revised = ("revised.csv", b"Parameter,Value\nPressure,12 bar\n", "text/csv")
    response = client.post(
        "/api/reports/csv",
        files={"reference": reference, "revised": revised},
    )
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "reference_source" in response.text


def test_invalid_report_format_is_rejected():
    reference = ("reference.csv", b"Parameter,Value\\nPressure,10 bar\\n", "text/csv")
    revised = ("revised.csv", b"Parameter,Value\\nPressure,12 bar\\n", "text/csv")
    response = client.post(
        "/api/reports/pdf",
        files={"reference": reference, "revised": revised},
    )
    assert response.status_code == 404
