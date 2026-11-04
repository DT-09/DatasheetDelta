from fastapi.testclient import TestClient

from datasheetdelta.api import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"


def test_investigation_endpoint_returns_source_linked_findings():
    reference = ("reference.csv", b"Parameter,Value\nPressure,10 bar\n", "text/csv")
    revised = ("revised.csv", b"Parameter,Value\nPressure,12 bar\n", "text/csv")
    response = client.post(
        "/api/investigations",
        files={"reference": reference, "revised": revised},
        data={"tolerances": "{}"},
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
    reference = ("reference.csv", b"Parameter,Value\nPressure,10 bar\n", "text/csv")
    revised = ("revised.csv", b"Parameter,Value\nPressure,12 bar\n", "text/csv")
    response = client.post(
        "/api/reports/pdf",
        files={"reference": reference, "revised": revised},
    )
    assert response.status_code == 404


def test_authenticated_review_lifecycle(tmp_path, monkeypatch):
    monkeypatch.setenv("DATASHEETDELTA_ACCESS_TOKEN", "test-secret-token")
    monkeypatch.setenv("DATASHEETDELTA_DB", str(tmp_path / "review.sqlite3"))
    headers = {"Authorization": "Bearer test-secret-token"}
    reference = ("reference.csv", b"Parameter,Value\nPressure,10 bar\n", "text/csv")
    revised = ("revised.csv", b"Parameter,Value\nPressure,12 bar\n", "text/csv")

    denied = client.post(
        "/api/investigations",
        files={"reference": reference, "revised": revised},
    )
    assert denied.status_code == 401

    created = client.post(
        "/api/investigations",
        headers=headers,
        files={"reference": reference, "revised": revised},
    )
    assert created.status_code == 200
    investigation_id = created.json()["investigation_id"]
    assert created.json()["review_enabled"] is True
    saved_list = client.get("/api/investigations", headers=headers)
    assert saved_list.status_code == 200
    assert saved_list.json()["investigations"][0]["id"] == investigation_id

    review = client.post(
        f"/api/investigations/{investigation_id}/reviews",
        headers=headers,
        json={
            "parameter": "pressure",
            "decision": "confirmed_change",
            "reviewer": "Test Reviewer",
            "note": "Checked against source document.",
        },
    )
    assert review.status_code == 200
    assert review.json()["review_chain_valid"] is True

    record = client.get(f"/api/investigations/{investigation_id}", headers=headers)
    assert record.status_code == 200
    assert record.json()["report_integrity_valid"] is True
    assert len(record.json()["review_events"]) == 1

    deleted = client.delete(f"/api/investigations/{investigation_id}", headers=headers)
    assert deleted.status_code == 200
    assert client.get(f"/api/investigations/{investigation_id}", headers=headers).status_code == 404


def test_synthetic_sample_files_are_served():
    reference = client.get("/examples/reference.csv")
    revised = client.get("/examples/revised.csv")
    assert reference.status_code == 200
    assert revised.status_code == 200
    assert "Parameter,Value" in reference.text
    assert "Maximum pressure" in revised.text
