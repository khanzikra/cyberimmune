"""
Tests for synthetic data generation.
"""
import tempfile
import os
import sqlite3
from src.data_generator import generate_history, generate_user_profile
from src.database import connect, create_schema, insert_events, get_events_count, get_user_event_counts


def test_same_seed_gives_identical_events():
    """Same seed should produce identical events."""
    events1 = generate_history(seed=42)
    events2 = generate_history(seed=42)
    assert len(events1) == len(events2)
    for e1, e2 in zip(events1, events2):
        assert e1 == e2


def test_different_seed_gives_different_events():
    """Different seeds should produce different events."""
    events1 = generate_history(seed=42)
    events2 = generate_history(seed=123)
    # At least one event should differ
    assert any(e1 != e2 for e1, e2 in zip(events1, events2))


def test_user_profile_deterministic():
    """User profile generation should be deterministic with same seed."""
    import random
    rng1 = random.Random(42)
    rng2 = random.Random(42)
    p1 = generate_user_profile(rng1, "user_01")
    p2 = generate_user_profile(rng2, "user_01")
    assert p1 == p2


def test_event_schema_valid():
    """Generated events should have valid schema."""
    events = generate_history(seed=42)
    for e in events:
        assert e["event_id"].startswith("EVT-")
        assert e["user_id"] in [f"user_{i:02d}" for i in range(1, 11)]
        assert e["event_type"] in ["login", "resource_access", "password_reset", "mfa_challenge"]
        assert e["outcome"] in ["success", "failure"]
        assert e["device_id"].startswith("device_")
        # Timestamp should be valid ISO format
        from datetime import datetime
        ts = datetime.fromisoformat(e["ts"].replace("Z", "+00:00"))
        assert ts.year == 2024


def test_database_rejects_invalid_event_type():
    """Database CHECK constraint should reject invalid event_type."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    conn = None
    try:
        conn = connect(db_path)
        create_schema(conn)
        cursor = conn.cursor()
        # Try to insert invalid event_type
        try:
            cursor.execute("""
                INSERT INTO events (event_id, ts, user_id, event_type, device_id, outcome, details)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, ("EVT-000001", "2024-01-01T12:00:00Z", "user_01", "invalid_type", "device_1", "success", "test"))
            conn.commit()
            assert False, "Should have raised exception"
        except sqlite3.IntegrityError:
            pass  # Expected
    finally:
        if conn:
            conn.close()
        os.unlink(db_path)


def test_database_rejects_invalid_outcome():
    """Database CHECK constraint should reject invalid outcome."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    conn = None
    try:
        conn = connect(db_path)
        create_schema(conn)
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO events (event_id, ts, user_id, event_type, device_id, outcome, details)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, ("EVT-000001", "2024-01-01T12:00:00Z", "user_01", "login", "device_1", "invalid", "test"))
            conn.commit()
            assert False, "Should have raised exception"
        except sqlite3.IntegrityError:
            pass  # Expected
    finally:
        if conn:
            conn.close()
        os.unlink(db_path)


def test_database_rejects_invalid_context_type():
    """Database CHECK constraint should reject invalid record_type."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    conn = None
    try:
        conn = connect(db_path)
        create_schema(conn)
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO context_records (record_id, ts, user_id, record_type, summary, status)
                VALUES (?, ?, ?, ?, ?, ?)
            """, ("CTX-0001", "2024-01-01T12:00:00Z", "user_01", "invalid_type", "test", "open"))
            conn.commit()
            assert False, "Should have raised exception"
        except sqlite3.IntegrityError:
            pass  # Expected
    finally:
        if conn:
            conn.close()
        os.unlink(db_path)


def test_row_counts():
    """Test row counts per user."""
    events = generate_history(seed=42)
    assert len(events) > 0

    # All 10 users should have events
    user_ids = set(e["user_id"] for e in events)
    assert len(user_ids) == 10

    # Each user should have reasonable number of events (8-15/day * 30 days = 240-450)
    from collections import Counter
    counts = Counter(e["user_id"] for e in events)
    for user_id, count in counts.items():
        assert 200 < count < 500, f"{user_id}: {count} events"


def test_night_workers_exist():
    """user_03 and user_07 should have night-time patterns."""
    import random
    rng = random.Random(42)
    p3 = generate_user_profile(rng, "user_03")
    p7 = generate_user_profile(rng, "user_07")
    assert p3["is_night_worker"] is True
    assert p7["is_night_worker"] is True

    # Others should not be night workers
    for i in [1, 2, 4, 5, 6, 8, 9, 10]:
        rng2 = random.Random(42)
        p = generate_user_profile(rng2, f"user_{i:02d}")
        assert p["is_night_worker"] is False, f"user_{i:02d} should not be night worker"


if __name__ == "__main__":
    test_same_seed_gives_identical_events()
    test_different_seed_gives_different_events()
    test_user_profile_deterministic()
    test_event_schema_valid()
    test_database_rejects_invalid_event_type()
    test_database_rejects_invalid_outcome()
    test_database_rejects_invalid_context_type()
    test_row_counts()
    test_night_workers_exist()
    print("All test_data.py tests passed!")