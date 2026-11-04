from fastapi.testclient import TestClient
from datasheetdelta.api import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["version"] == "1.1.0"

def test_pages_origin_can_call_api():
    response = client.options(
        "/api/investigations",
        headers={
            "Origin": "https://datasheetdelta.pages.dev",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://datasheetdelta.pages.dev"

def test_workspace_is_served_by_api_host():
    response = client.get("/")
    assert response.status_code == 200
    assert "Engineering revision intelligence" in response.text

def test_investigation_endpoint_returns_traceable_findings():
    response = client.post(
        "/api/investigations",
        files={
            "reference": ("reference.csv", b"Parameter,Value\nPressure,10 bar\n", "text/csv"),
            "revised": ("revised.csv", b"Parameter,Value\nPressure,12 bar\n", "text/csv"),
        },
        data={"tolerance": "0"},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["summary"]["changed"] == 1
    assert result["findings"][0]["reference_source"] == "row 2"
    assert result["review_required"] is True

def test_unsupported_upload_is_rejected():
    response = client.post(
        "/api/investigations",
        files={
            "reference": ("reference.exe", b"no", "application/octet-stream"),
            "revised": ("revised.csv", b"Pressure,10 bar", "text/csv"),
        },
    )
    assert response.status_code == 415

def test_csv_export_endpoint():
    response = client.post(
        "/api/reports/csv",
        files={
            "reference": ("reference.csv", b"Pressure,10 bar", "text/csv"),
            "revised": ("revised.csv", b"Pressure,12 bar", "text/csv"),
        },
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "unit" not in response.text.lower()
    assert "pressure" in response.text.lower()
