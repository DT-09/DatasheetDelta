from fastapi.testclient import TestClient

from datasheetdelta.api import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["version"] == "1.0.0"

def test_workspace_is_served():
    response = client.get("/")
    assert response.status_code == 200
    assert "DatasheetDelta" in response.text

def test_investigation_endpoint_returns_provenance_and_findings():
    response = client.post(
        "/api/investigations",
        files={
            "reference": ("old.csv", b"Parameter,Value\nPressure,1 bar\n", "text/csv"),
            "revised": ("new.csv", b"Parameter,Value\nPressure,100 kPa\n", "text/csv"),
        },
        data={"tolerance": "0"},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["findings"][0]["status"] == "unchanged"
    assert result["findings"][0]["reference_source"] == "row 2"
    assert result["findings"][0]["reference_excerpt"] == "Pressure: 1 bar"
    assert result["review_required"] is True

def test_unsupported_extension_is_rejected():
    response = client.post(
        "/api/investigations",
        files={
            "reference": ("old.exe", b"no", "application/octet-stream"),
            "revised": ("new.csv", b"Parameter,Value\nPressure,1 bar\n", "text/csv"),
        },
    )
    assert response.status_code == 415

def test_empty_upload_is_rejected():
    response = client.post(
        "/api/investigations",
        files={
            "reference": ("old.csv", b"", "text/csv"),
            "revised": ("new.csv", b"Parameter,Value\nPressure,1 bar\n", "text/csv"),
        },
    )
    assert response.status_code == 400

def test_json_export_endpoint():
    response = client.post(
        "/api/reports/json",
        files={
            "reference": ("old.csv", b"Pressure,1 bar\n", "text/csv"),
            "revised": ("new.csv", b"Pressure,2 bar\n", "text/csv"),
        },
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert "attachment" in response.headers["content-disposition"]

def test_pdf_export_endpoint_returns_pdf_document():
    response = client.post(
        "/api/reports/pdf",
        files={
            "reference": ("old.csv", b"Pressure,1 bar\\n", "text/csv"),
            "revised": ("new.csv", b"Pressure,2 bar\\n", "text/csv"),
        },
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF-")


def test_upload_limit_is_enforced(monkeypatch):
    import datasheetdelta.api as api_module

    monkeypatch.setattr(api_module, "MAX_FILE_BYTES", 8)
    response = client.post(
        "/api/investigations",
        files={
            "reference": ("old.csv", b"Pressure,10 bar", "text/csv"),
            "revised": ("new.csv", b"Pressure,12 bar", "text/csv"),
        },
    )
    assert response.status_code == 413

def test_non_finite_tolerance_is_rejected():
    response = client.post(
        "/api/investigations",
        files={
            "reference": ("old.csv", b"Pressure,10 bar", "text/csv"),
            "revised": ("new.csv", b"Pressure,12 bar", "text/csv"),
        },
        data={"tolerance": "nan"},
    )
    assert response.status_code == 422
