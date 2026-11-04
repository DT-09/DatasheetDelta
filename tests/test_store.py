import pytest

from datasheetdelta import store


def test_investigation_persists_report_and_review_chain(tmp_path, monkeypatch):
    monkeypatch.setenv("DATASHEETDELTA_DB", str(tmp_path / "records.sqlite3"))
    report = {
        "reference_file": "before.csv",
        "revised_file": "after.csv",
        "findings": [{"parameter": "pressure", "status": "changed"}],
    }
    saved = store.save_investigation(report)
    first = store.add_review(
        saved["investigation_id"], "pressure", "confirmed_change", "Engineer A", "Verified against drawing."
    )
    second = store.add_review(
        saved["investigation_id"], "pressure", "needs_follow_up", "Engineer B", "Check supplier note."
    )

    record = store.get_investigation(saved["investigation_id"])
    assert record["report"] == report
    assert record["report_integrity_valid"] is True
    assert record["review_chain_valid"] is True
    assert [event["id"] for event in record["review_events"]] == [first["id"], second["id"]]
    assert all(event["event_hash"] and event["previous_hash"] for event in record["review_events"])


def test_review_rejects_unknown_parameter_and_invalid_decision(tmp_path, monkeypatch):
    monkeypatch.setenv("DATASHEETDELTA_DB", str(tmp_path / "records.sqlite3"))
    report = {
        "reference_file": "before.csv",
        "revised_file": "after.csv",
        "findings": [{"parameter": "pressure", "status": "changed"}],
    }
    saved = store.save_investigation(report)
    with pytest.raises(ValueError):
        store.add_review(saved["investigation_id"], "unknown", "confirmed_change", "Reviewer")
    with pytest.raises(ValueError):
        store.add_review(saved["investigation_id"], "pressure", "approved", "Reviewer")


def test_review_events_are_append_only(tmp_path, monkeypatch):
    monkeypatch.setenv("DATASHEETDELTA_DB", str(tmp_path / "records.sqlite3"))
    report = {
        "reference_file": "before.csv",
        "revised_file": "after.csv",
        "findings": [{"parameter": "pressure", "status": "changed"}],
    }
    saved = store.save_investigation(report)
    event = store.add_review(saved["investigation_id"], "pressure", "confirmed_change", "Reviewer")
    with store._database() as connection:
        with pytest.raises(Exception):
            connection.execute("UPDATE review_events SET note = 'tampered' WHERE id = ?", (event["id"],))


def test_review_hash_chain_detects_database_tampering(tmp_path, monkeypatch):
    monkeypatch.setenv("DATASHEETDELTA_DB", str(tmp_path / "records.sqlite3"))
    report = {
        "reference_file": "before.csv",
        "revised_file": "after.csv",
        "findings": [{"parameter": "pressure", "status": "changed"}],
    }
    saved = store.save_investigation(report)
    event = store.add_review(saved["investigation_id"], "pressure", "confirmed_change", "Reviewer")
    with store._database() as connection:
        connection.execute("DROP TRIGGER review_events_no_update")
        connection.execute("UPDATE review_events SET note = 'tampered' WHERE id = ?", (event["id"],))
    record = store.get_investigation(saved["investigation_id"])
    assert record["review_chain_valid"] is False
