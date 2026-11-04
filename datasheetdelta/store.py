from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


GENESIS = "0" * 64
DECISIONS = {"confirmed_change", "not_material", "needs_follow_up"}


def _database_path() -> Path:
    configured = os.getenv("DATASHEETDELTA_DB", ".datasheetdelta/datasheetdelta.sqlite3")
    return Path(configured).expanduser()


def _connect() -> sqlite3.Connection:
    path = _database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=15)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    return connection


@contextmanager
def _database():
    connection = _connect()
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize() -> None:
    with _database() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS investigations (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                reference_name TEXT NOT NULL,
                revised_name TEXT NOT NULL,
                report_json TEXT NOT NULL,
                report_sha256 TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS review_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                investigation_id TEXT NOT NULL REFERENCES investigations(id) ON DELETE CASCADE,
                parameter TEXT NOT NULL,
                decision TEXT NOT NULL,
                reviewer TEXT NOT NULL,
                note TEXT NOT NULL,
                created_at TEXT NOT NULL,
                previous_hash TEXT NOT NULL,
                event_hash TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS review_events_investigation
                ON review_events(investigation_id, id);
            CREATE TRIGGER IF NOT EXISTS review_events_no_update
                BEFORE UPDATE ON review_events
                BEGIN SELECT RAISE(ABORT, 'review events are append-only'); END;
            CREATE TRIGGER IF NOT EXISTS review_events_no_delete
                BEFORE DELETE ON review_events
                BEGIN SELECT RAISE(ABORT, 'review events are append-only'); END;
            """
        )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical(value: dict[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def save_investigation(report: dict[str, Any]) -> dict[str, Any]:
    initialize()
    investigation_id = str(uuid.uuid4())
    created_at = _now()
    payload = json.dumps(report, ensure_ascii=False, separators=(",", ":"))
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    with _database() as connection:
        connection.execute(
            """INSERT INTO investigations
               (id, created_at, reference_name, revised_name, report_json, report_sha256)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                investigation_id, created_at, report["reference_file"],
                report["revised_file"], payload, digest,
            ),
        )
    return {"investigation_id": investigation_id, "created_at": created_at, "report_sha256": digest}


def _read_events(connection: sqlite3.Connection, investigation_id: str) -> tuple[list[dict[str, Any]], bool]:
    rows = connection.execute(
        """SELECT id, parameter, decision, reviewer, note, created_at,
                  previous_hash, event_hash
           FROM review_events WHERE investigation_id = ? ORDER BY id""",
        (investigation_id,),
    ).fetchall()
    events = [dict(row) for row in rows]
    previous = GENESIS
    valid = True
    for event in events:
        unsigned = {key: event[key] for key in (
            "id", "parameter", "decision", "reviewer", "note", "created_at", "previous_hash"
        )}
        expected = hashlib.sha256((previous + _canonical(unsigned)).encode("utf-8")).hexdigest()
        if event["previous_hash"] != previous or event["event_hash"] != expected:
            valid = False
        previous = event["event_hash"]
    return events, valid


def get_investigation(investigation_id: str) -> dict[str, Any] | None:
    initialize()
    with _database() as connection:
        row = connection.execute(
            "SELECT * FROM investigations WHERE id = ?", (investigation_id,)
        ).fetchone()
        if row is None:
            return None
        report = json.loads(row["report_json"])
        actual_digest = hashlib.sha256(row["report_json"].encode("utf-8")).hexdigest()
        events, chain_valid = _read_events(connection, investigation_id)
    return {
        "investigation_id": row["id"],
        "created_at": row["created_at"],
        "report_sha256": row["report_sha256"],
        "report_integrity_valid": actual_digest == row["report_sha256"],
        "review_chain_valid": chain_valid,
        "report": report,
        "review_events": events,
    }


def add_review(
    investigation_id: str,
    parameter: str,
    decision: str,
    reviewer: str,
    note: str = "",
) -> dict[str, Any]:
    if decision not in DECISIONS:
        raise ValueError("Decision must be confirmed_change, not_material or needs_follow_up.")
    reviewer = reviewer.strip()
    parameter = parameter.strip()
    note = note.strip()
    if not reviewer:
        raise ValueError("Reviewer name is required.")
    if not parameter:
        raise ValueError("Parameter is required.")
    if len(reviewer) > 120 or len(note) > 4000:
        raise ValueError("Reviewer name or note exceeds the allowed length.")

    initialize()
    with _database() as connection:
        connection.execute("BEGIN IMMEDIATE")
        investigation = connection.execute(
            "SELECT report_json FROM investigations WHERE id = ?", (investigation_id,)
        ).fetchone()
        if investigation is None:
            raise KeyError("Investigation not found.")
        report = json.loads(investigation["report_json"])
        if parameter not in {item["parameter"] for item in report["findings"]}:
            raise ValueError("Parameter does not exist in this investigation.")
        previous_row = connection.execute(
            "SELECT event_hash FROM review_events WHERE investigation_id = ? ORDER BY id DESC LIMIT 1",
            (investigation_id,),
        ).fetchone()
        previous_hash = previous_row["event_hash"] if previous_row else GENESIS
        created_at = _now()
        event_id = connection.execute(
            "SELECT COALESCE(MAX(id), 0) + 1 FROM review_events"
        ).fetchone()[0]
        unsigned = {
            "id": event_id, "parameter": parameter, "decision": decision,
            "reviewer": reviewer, "note": note, "created_at": created_at,
            "previous_hash": previous_hash,
        }
        event_hash = hashlib.sha256(
            (previous_hash + _canonical(unsigned)).encode("utf-8")
        ).hexdigest()
        connection.execute(
            """INSERT INTO review_events
               (id, investigation_id, parameter, decision, reviewer, note, created_at, previous_hash, event_hash)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (event_id, investigation_id, parameter, decision, reviewer, note, created_at, previous_hash, event_hash),
        )
    return {
        "id": event_id, "parameter": parameter, "decision": decision,
        "reviewer": reviewer, "note": note, "created_at": created_at,
    }


def delete_investigation(investigation_id: str) -> bool:
    initialize()
    with _database() as connection:
        connection.execute("BEGIN IMMEDIATE")
        # The full record and its review history are removed together on explicit request.
        connection.execute("DROP TRIGGER IF EXISTS review_events_no_delete")
        cursor = connection.execute("DELETE FROM investigations WHERE id = ?", (investigation_id,))
        connection.execute(
            """CREATE TRIGGER review_events_no_delete
               BEFORE DELETE ON review_events
               BEGIN SELECT RAISE(ABORT, 'review events are append-only'); END"""
        )
        return cursor.rowcount > 0


def list_investigations(limit: int = 50) -> list[dict[str, Any]]:
    if not isinstance(limit, int) or limit < 1 or limit > 100:
        raise ValueError("Investigation list limit must be between 1 and 100.")
    initialize()
    with _database() as connection:
        rows = connection.execute(
            """SELECT id, created_at, reference_name, revised_name, report_sha256
               FROM investigations ORDER BY created_at DESC LIMIT ?""",
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]
