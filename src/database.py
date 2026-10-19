"""
Database schema and helpers for CyberImmune synthetic data.
"""
import sqlite3
from typing import List, Dict, Any
from pathlib import Path


EVENT_TYPES = ("login", "resource_access", "password_reset", "mfa_challenge")
OUTCOMES = ("success", "failure")
RECORD_TYPES = ("it_ticket", "approved_device", "travel_notice", "hr_note")


def connect(path: str) -> sqlite3.Connection:
    """Open a read-write SQLite connection with foreign keys on."""
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn


def create_schema(conn: sqlite3.Connection) -> None:
    """Create events and context_records tables with CHECK constraints."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS events (
            event_id TEXT PRIMARY KEY,
            ts TEXT NOT NULL,
            user_id TEXT NOT NULL,
            event_type TEXT NOT NULL CHECK (event_type IN ('login', 'resource_access', 'password_reset', 'mfa_challenge')),
            device_id TEXT,
            resource TEXT,
            source_ip TEXT,
            outcome TEXT NOT NULL CHECK (outcome IN ('success', 'failure')),
            details TEXT
        );

        CREATE TABLE IF NOT EXISTS context_records (
            record_id TEXT PRIMARY KEY,
            ts TEXT NOT NULL,
            user_id TEXT NOT NULL,
            record_type TEXT NOT NULL CHECK (record_type IN ('it_ticket', 'approved_device', 'travel_notice', 'hr_note')),
            device_id TEXT,
            summary TEXT,
            status TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_events_user_ts ON events(user_id, ts);
        CREATE INDEX IF NOT EXISTS idx_events_user_type_ts ON events(user_id, event_type, ts);
        CREATE INDEX IF NOT EXISTS idx_context_user_ts ON context_records(user_id, ts);
    """)


def insert_events(conn: sqlite3.Connection, rows: List[Dict[str, Any]]) -> None:
    """Insert multiple event rows."""
    if not rows:
        return
    placeholders = ", ".join(["(?, ?, ?, ?, ?, ?, ?, ?, ?)"] * len(rows))
    flat = []
    for r in rows:
        flat.extend([
            r["event_id"], r["ts"], r["user_id"], r["event_type"],
            r.get("device_id"), r.get("resource"), r.get("source_ip"),
            r["outcome"], r.get("details", "")
        ])
    conn.execute(f"INSERT INTO events VALUES {placeholders}", flat)


def insert_context(conn: sqlite3.Connection, rows: List[Dict[str, Any]]) -> None:
    """Insert multiple context record rows."""
    if not rows:
        return
    placeholders = ", ".join(["(?, ?, ?, ?, ?, ?, ?)"] * len(rows))
    flat = []
    for r in rows:
        flat.extend([
            r["record_id"], r["ts"], r["user_id"], r["record_type"],
            r.get("device_id"), r.get("summary", ""), r.get("status", "")
        ])
    conn.execute(f"INSERT INTO context_records VALUES {placeholders}", flat)


if __name__ == "__main__":
    # Quick manual test
    db_path = Path(__file__).parent.parent / "data" / "test.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = connect(str(db_path))
    create_schema(conn)
    conn.close()
    print(f"Schema created at {db_path}")