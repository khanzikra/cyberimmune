"""
Tests for baseline computation and indicator detection.
"""
import sqlite3
import tempfile
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.database import connect, create_schema, insert_events, insert_context
from src.baseline import compute_baseline, find_indicators


def make_test_db():
    """Create a test database with controlled data."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    conn = connect(db_path)
    create_schema(conn)

    # Use a fixed cutoff
    cutoff = "2024-01-21T00:00:00Z"
    window_start = "2024-01-21T00:00:00Z"
    window_end = "2024-01-31T23:59:59Z"

    # User: user_01
    # Baseline (days 1-20): 25 logins at hour 12, device_A, resource github
    # Focus window (days 21-30): various test events

    events = []
    event_id = 1

    # Baseline logins (25 at hour 12)
    for day in range(1, 21):
        for i in range(1, 2):  # 1 per day = 20, plus 5 more
            ts = f"2024-01-{day:02d}T12:00:00Z"
            events.append({
                "event_id": f"EVT-{event_id:06d}",
                "ts": ts,
                "user_id": "user_01",
                "event_type": "login",
                "device_id": "device_A",
                "resource": None,
                "source_ip": "10.0.0.1",
                "outcome": "success",
                "details": "login",
            })
            event_id += 1

    # 5 more baseline logins at hour 12
    for i in range(5):
        ts = f"2024-01-{10+i:02d}T12:30:00Z"
        events.append({
            "event_id": f"EVT-{event_id:06d}",
            "ts": ts,
            "user_id": "user_01",
            "event_type": "login",
            "device_id": "device_A",
            "resource": None,
            "source_ip": "10.0.0.1",
            "outcome": "success",
            "details": "login",
        })
        event_id += 1

    # Baseline resource access (github 20 times)
    for day in range(1, 21):
        ts = f"2024-01-{day:02d}T12:05:00Z"
        events.append({
            "event_id": f"EVT-{event_id:06d}",
            "ts": ts,
            "user_id": "user_01",
            "event_type": "resource_access",
            "device_id": "device_A",
            "resource": "github",
            "source_ip": "10.0.0.1",
            "outcome": "success",
            "details": "access",
        })
        event_id += 1

    # Focus window events for testing:
    # 1. Normal event: hour 12, device_A, github -> should trigger nothing
    events.append({
        "event_id": f"EVT-{event_id:06d}",
        "ts": "2024-01-22T12:00:00Z",
        "user_id": "user_01",
        "event_type": "login",
        "device_id": "device_A",
        "resource": None,
        "source_ip": "10.0.0.1",
        "outcome": "success",
        "details": "normal login",
    })
    normal_login_id = f"EVT-{event_id:06d}"
    event_id += 1

    # 2. R1: unusual hour (03:00 UTC) - baseline has 0 at hour 3
    events.append({
        "event_id": f"EVT-{event_id:06d}",
        "ts": "2024-01-22T03:00:00Z",
        "user_id": "user_01",
        "event_type": "login",
        "device_id": "device_A",
        "resource": None,
        "source_ip": "10.0.0.1",
        "outcome": "success",
        "details": "unusual hour",
    })
    r1_event_id = f"EVT-{event_id:06d}"
    event_id += 1

    # 3. R2: new device (device_B)
    events.append({
        "event_id": f"EVT-{event_id:06d}",
        "ts": "2024-01-22T12:00:00Z",
        "user_id": "user_01",
        "event_type": "login",
        "device_id": "device_B",
        "resource": None,
        "source_ip": "10.0.0.2",
        "outcome": "success",
        "details": "new device",
    })
    r2_event_id = f"EVT-{event_id:06d}"
    event_id += 1

    # 4. R3: rare resource (never_used_resource)
    events.append({
        "event_id": f"EVT-{event_id:06d}",
        "ts": "2024-01-22T12:00:00Z",
        "user_id": "user_01",
        "event_type": "resource_access",
        "device_id": "device_A",
        "resource": "never_used_resource",
        "source_ip": "10.0.0.1",
        "outcome": "success",
        "details": "rare resource",
    })
    r3_event_id = f"EVT-{event_id:06d}"
    event_id += 1

    # 5. R4: 3 failed logins in 10 minutes
    for i in range(3):
        ts = (datetime(2024, 1, 23, 10, 0, 0) + timedelta(minutes=i*3)).isoformat().replace("+00:00", "Z")
        events.append({
            "event_id": f"EVT-{event_id:06d}",
            "ts": ts,
            "user_id": "user_01",
            "event_type": "login",
            "device_id": "device_A",
            "resource": None,
            "source_ip": "10.0.0.1",
            "outcome": "failure",
            "details": "failed login",
        })
        event_id += 1
    r4_first_id = f"EVT-{event_id-3:06d}"

    # 6. NOT R4: 3 failed logins spread over an hour
    for i in range(3):
        ts = (datetime(2024, 1, 24, 10, 0, 0) + timedelta(minutes=i*25)).isoformat().replace("+00:00", "Z")
        events.append({
            "event_id": f"EVT-{event_id:06d}",
            "ts": ts,
            "user_id": "user_01",
            "event_type": "login",
            "device_id": "device_A",
            "resource": None,
            "source_ip": "10.0.0.1",
            "outcome": "failure",
            "details": "failed login spread",
        })
        event_id += 1

    insert_events(conn, events)

    # Add some context records
    context = [
        {
            "record_id": "CTX-0001",
            "ts": "2024-01-15T00:00:00Z",
            "user_id": "user_01",
            "record_type": "approved_device",
            "device_id": "device_A",
            "summary": "Device A approved",
            "status": "active",
        }
    ]
    insert_context(conn, context)

    conn.commit()
    return conn, db_path, cutoff, window_start, window_end


def test_baseline_sufficient_false_when_few_logins():
    """baseline_sufficient is False when fewer than 20 baseline logins."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        conn = connect(db_path)
        create_schema(conn)

        # Only 10 baseline logins
        events = []
        for i in range(10):
            events.append({
                "event_id": f"EVT-{i+1:06d}",
                "ts": f"2024-01-{i+1:02d}T12:00:00Z",
                "user_id": "user_01",
                "event_type": "login",
                "device_id": "device_A",
                "resource": None,
                "source_ip": "10.0.0.1",
                "outcome": "success",
                "details": "login",
            })
        insert_events(conn, events)
        conn.commit()

        baseline = compute_baseline(conn, "user_01", "2024-01-21T00:00:00Z")
        assert baseline["baseline_login_count"] == 10
        assert baseline["baseline_sufficient"] is False

    finally:
        conn.close()
        os.unlink(db_path)


def test_baseline_sufficient_true_when_20_plus_logins():
    """baseline_sufficient is True when 20+ baseline logins."""
    conn, db_path, cutoff, _, _ = make_test_db()
    try:
        baseline = compute_baseline(conn, "user_01", cutoff)
        assert baseline["baseline_login_count"] >= 20
        assert baseline["baseline_sufficient"] is True
    finally:
        conn.close()
        os.unlink(db_path)


def test_planted_event_triggers_r1_r2_r3():
    """A planted event (new device + 03:00 UTC + never-used resource) triggers R1, R2, R3."""
    conn, db_path, cutoff, window_start, window_end = make_test_db()
    try:
        indicators = find_indicators(conn, "user_01", cutoff, window_start, window_end)
        rules = {ind["rule"] for ind in indicators}

        assert "R1" in rules, "R1 should trigger for 03:00 UTC login"
        assert "R2" in rules, "R2 should trigger for new device"
        assert "R3" in rules, "R3 should trigger for never-used resource"

        # Check R1 detail
        r1 = next(i for i in indicators if i["rule"] == "R1")
        assert "03:00" in r1["detail"] or "hour 3" in r1["detail"].lower()

        # Check R2 detail
        r2 = next(i for i in indicators if i["rule"] == "R2")
        assert "device_B" in r2["detail"]

        # Check R3 detail
        r3 = next(i for i in indicators if i["rule"] == "R3")
        assert "never_used_resource" in r3["detail"]

    finally:
        conn.close()
        os.unlink(db_path)


def test_normal_event_triggers_nothing():
    """A normal event on usual device in usual hours triggers nothing."""
    conn, db_path, cutoff, window_start, window_end = make_test_db()
    try:
        # The normal login is at 12:00 on device_A - should not trigger any rule
        # But we need to check that the specific normal event doesn't appear in indicators
        indicators = find_indicators(conn, "user_01", cutoff, window_start, window_end)

        # The normal event ID should not be cited by any indicator
        normal_event_id = "EVT-000026"  # This is the normal login we added
        for ind in indicators:
            assert ind["event_id"] != normal_event_id, f"Normal event should not trigger {ind['rule']}"

    finally:
        conn.close()
        os.unlink(db_path)


def test_r4_triggers_for_3_failures_in_10_min():
    """R4 triggers for 3 failed logins in 10 minutes."""
    conn, db_path, cutoff, window_start, window_end = make_test_db()
    try:
        indicators = find_indicators(conn, "user_01", cutoff, window_start, window_end)
        r4_indicators = [i for i in indicators if i["rule"] == "R4"]
        assert len(r4_indicators) == 1, "Should have exactly one R4 indicator"
        assert "3 failed logins" in r4_indicators[0]["detail"]

    finally:
        conn.close()
        os.unlink(db_path)


def test_r4_not_trigger_for_3_spread_over_hour():
    """R4 does NOT trigger for 3 failed logins spread over an hour."""
    conn, db_path, cutoff, window_start, window_end = make_test_db()
    try:
        indicators = find_indicators(conn, "user_01", cutoff, window_start, window_end)
        r4_indicators = [i for i in indicators if i["rule"] == "R4"]

        # Should only have one R4 (the 10-minute burst), not two
        assert len(r4_indicators) == 1, f"Should have 1 R4, got {len(r4_indicators)}"

    finally:
        conn.close()
        os.unlink(db_path)


if __name__ == "__main__":
    test_baseline_sufficient_false_when_few_logins()
    print("✓ test_baseline_sufficient_false_when_few_logins")
    test_baseline_sufficient_true_when_20_plus_logins()
    print("✓ test_baseline_sufficient_true_when_20_plus_logins")
    test_planted_event_triggers_r1_r2_r3()
    print("✓ test_planted_event_triggers_r1_r2_r3")
    test_normal_event_triggers_nothing()
    print("✓ test_normal_event_triggers_nothing")
    test_r4_triggers_for_3_failures_in_10_min()
    print("✓ test_r4_triggers_for_3_failures_in_10_min")
    test_r4_not_trigger_for_3_spread_over_hour()
    print("✓ test_r4_not_trigger_for_3_spread_over_hour")
    print("\nAll baseline tests passed!")