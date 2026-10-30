"""
Database schema and helpers for CyberImmune synthetic data.
"""
import sqlite3
from pathlib import Path
from typing import List, Dict, Any


def connect(db_path: str) -> sqlite3.Connection:
    """Create a connection to the SQLite database."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def create_schema(conn: sqlite3.Connection) -> None:
    """Create tables with CHECK constraints for allowlists."""
    cursor = conn.cursor()

    # events table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            event_id TEXT PRIMARY KEY,
            ts TEXT NOT NULL,
            user_id TEXT NOT NULL,
            event_type TEXT NOT NULL CHECK (event_type IN ('login', 'resource_access', 'password_reset', 'mfa_challenge')),
            device_id TEXT NOT NULL,
            resource TEXT,
            source_ip TEXT,
            outcome TEXT NOT NULL CHECK (outcome IN ('success', 'failure')),
            details TEXT
        )
    """)

    # context_records table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS context_records (
            record_id TEXT PRIMARY KEY,
            ts TEXT NOT NULL,
            user_id TEXT NOT NULL,
            record_type TEXT NOT NULL CHECK (record_type IN ('it_ticket', 'approved_device', 'travel_notice', 'hr_note')),
            device_id TEXT,
            summary TEXT,
            status TEXT
        )
    """)

    # indexes for common queries
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_user_ts ON events(user_id, ts)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_user_type ON events(user_id, event_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_context_user_ts ON context_records(user_id, ts)")

    conn.commit()


def insert_events(conn: sqlite3.Connection, rows: List[Dict[str, Any]]) -> None:
    """Insert event rows into the database."""
    cursor = conn.cursor()
    cursor.executemany("""
        INSERT INTO events (event_id, ts, user_id, event_type, device_id, resource, source_ip, outcome, details)
        VALUES (:event_id, :ts, :user_id, :event_type, :device_id, :resource, :source_ip, :outcome, :details)
    """, rows)
    conn.commit()


def insert_context(conn: sqlite3.Connection, rows: List[Dict[str, Any]]) -> None:
    """Insert context record rows into the database."""
    cursor = conn.cursor()
    cursor.executemany("""
        INSERT INTO context_records (record_id, ts, user_id, record_type, device_id, summary, status)
        VALUES (:record_id, :ts, :user_id, :record_type, :device_id, :summary, :status)
    """, rows)
    conn.commit()


def get_events_count(conn: sqlite3.Connection) -> int:
    """Get total count of events."""
    cursor = conn.cursor()
    return cursor.execute("SELECT COUNT(*) FROM events").fetchone()[0]


def get_context_count(conn: sqlite3.Connection) -> int:
    """Get total count of context records."""
    cursor = conn.cursor()
    return cursor.execute("SELECT COUNT(*) FROM context_records").fetchone()[0]


def get_user_event_counts(conn: sqlite3.Connection) -> Dict[str, int]:
    """Get event count per user."""
    cursor = conn.cursor()
    rows = cursor.execute("SELECT user_id, COUNT(*) as cnt FROM events GROUP BY user_id ORDER BY user_id").fetchall()
    return {row["user_id"]: row["cnt"] for row in rows}


if __name__ == "__main__":
    import sys
    db_path = sys.argv[1] if len(sys.argv) > 1 else "data/history.db"
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = connect(db_path)
    create_schema(conn)
    print(f"Schema created at {db_path}")
    conn.close()