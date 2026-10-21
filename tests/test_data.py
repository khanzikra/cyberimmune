"""
Tests for data generation and database schema.
"""
import sqlite3
import tempfile
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.database import connect, create_schema, insert_events, insert_context
from src.data_generator import generate_history, generate_user_profile
from src.baseline import compute_baseline, find_indicators


def test_deterministic_generation():
    """Same seed gives identical events; different seed differs."""
    data1 = generate_history(seed=42)
    data2 = generate_history(seed=42)
    data3 = generate_history(seed=123)

    # Same seed = identical
    assert len(data1["events"]) == len(data2["events"])
    for e1, e2 in zip(data1["events"], data2["events"]):
        assert e1 == e2

    assert len(data1["context_records"]) == len(data2["context_records"])
    for c1, c2 in zip(data1["context_records"], data2["context_records"]):
        assert c1 == c2

    # Different seed = different (at least one event differs)
    assert data1["events"] != data3["events"]


def test_schema_rejects_invalid_event_type():
    """Schema should reject invalid event_type."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        conn = connect(db_path)
        create_schema(conn)

        # Valid event should work
        insert_events(conn, [{
            "event_id": "EVT-000001",
            "ts": "2024-01-01T12:00:00Z",
            "user_id": "user_01",
            "event_type": "login",
            "device_id": "device_a",
            "resource": None,
            "source_ip": "10.0.0.1",
            "outcome": "success",
            "details": "test",
        }])
        conn.commit()

        # Invalid event_type should fail
        try:
            insert_events(conn, [{
                "event_id": "EVT-000002",
                "ts": "2024-01-01T12:00:00Z",
                "user_id": "user_01",
                "event_type": "invalid_type",
                "device_id": "device_a",
                "resource": None,
                "source_ip": "10.0.0.1",
                "outcome": "success",
                "details": "test",
            }])
            conn.commit()
            assert False, "Should have raised IntegrityError"
        except sqlite3.IntegrityError:
            pass  # Expected

    finally:
        conn.close()
        os.unlink(db_path)


def test_user_profile_structure():
    """User profile has expected structure."""
    import random
    rng = random.Random(42)
    profile = generate_user_profile(rng, "user_01")

    assert "devices" in profile
    assert 1 <= len(profile["devices"]) <= 2
    assert "work_start" in profile
    assert 7 <= profile["work_start"] <= 10
    assert "work_end" in profile
    assert 16 <= profile["work_end"] <= 19
    assert "regular_resources" in profile
    assert 4 <= len(profile["regular_resources"]) <= 8
    assert "night_worker" in profile


def test_event_count_per_user():
    """Each user should have reasonable event count over 30 days."""
    data = generate_history(seed=42)
    user_counts = {}
    for e in data["events"]:
        user_counts[e["user_id"]] = user_counts.get(e["user_id"], 0) + 1

    for user_id in [f"user_{i:02d}" for i in range(1, 11)]:
        assert user_id in user_counts
        # ~10 events/day * 30 days = ~300, but weekends less
        assert 150 <= user_counts[user_id] <= 500


def test_timestamps_format():
    """All timestamps should be ISO 8601 UTC ending in Z."""
    data = generate_history(seed=42)
    for e in data["events"]:
        assert e["ts"].endswith("Z")
        # Should be parseable
        from datetime import datetime
        dt = datetime.fromisoformat(e["ts"].replace("Z", "+00:00"))
        assert dt.tzinfo is not None

    for c in data["context_records"]:
        assert c["ts"].endswith("Z")


if __name__ == "__main__":
    test_deterministic_generation()
    print("✓ test_deterministic_generation")
    test_schema_rejects_invalid_event_type()
    print("✓ test_schema_rejects_invalid_event_type")
    test_user_profile_structure()
    print("✓ test_user_profile_structure")
    test_event_count_per_user()
    print("✓ test_event_count_per_user")
    test_timestamps_format()
    print("✓ test_timestamps_format")
    print("\nAll data tests passed!")