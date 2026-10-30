"""
Tests for baseline computation and indicator detection.
"""
import tempfile
import os
from datetime import datetime, timezone, timedelta
import sqlite3

from src.database import connect, create_schema, insert_events
from src.baseline import compute_baseline, find_indicators


def create_test_db():
    """Create a test database with known data."""
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)
    conn = connect(db_path)
    create_schema(conn)
    return conn, db_path


def setup_baseline_events(conn, user_id="user_01"):
    """Insert baseline events for testing."""
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)

    # 30 baseline logins spread across work hours (9-17)
    events = []
    for i in range(30):
        hour = 9 + (i % 8)  # 9-16
        ts = base.replace(hour=hour, minute=i*2, second=0)
        events.append({
            "event_id": f"EVT-{i+1:06d}",
            "ts": ts.isoformat().replace("+00:00", "Z"),
            "user_id": user_id,
            "event_type": "login",
            "device_id": "device_A",
            "resource": None,
            "source_ip": "10.0.0.1",
            "outcome": "success",
            "details": "Normal login",
        })

    # Some resource accesses
    for i, res in enumerate(["email", "github", "slack", "email", "github"]):
        ts = base.replace(hour=10+i, minute=0, second=0)
        events.append({
            "event_id": f"EVT-{100+i:06d}",
            "ts": ts.isoformat().replace("+00:00", "Z"),
            "user_id": user_id,
            "event_type": "resource_access",
            "device_id": "device_A",
            "resource": res,
            "source_ip": "10.0.0.1",
            "outcome": "success",
            "details": f"Accessed {res}",
        })

    insert_events(conn, events)
    return events


def test_baseline_sufficient_true():
    """baseline_sufficient should be True with >=20 logins."""
    conn, db_path = create_test_db()
    try:
        setup_baseline_events(conn)
        cutoff = "2024-01-02T00:00:00Z"
        baseline = compute_baseline(conn, "user_01", cutoff)
        assert baseline["baseline_login_count"] == 30
        assert baseline["baseline_sufficient"] is True
    finally:
        conn.close()
        os.unlink(db_path)


def test_baseline_sufficient_false():
    """baseline_sufficient should be False with <20 logins."""
    conn, db_path = create_test_db()
    try:
        # Only 10 logins
        base = datetime(2024, 1, 1, tzinfo=timezone.utc)
        events = []
        for i in range(10):
            ts = base.replace(hour=10, minute=i*5, second=0)
            events.append({
                "event_id": f"EVT-{i+1:06d}",
                "ts": ts.isoformat().replace("+00:00", "Z"),
                "user_id": "user_01",
                "event_type": "login",
                "device_id": "device_A",
                "resource": None,
                "source_ip": "10.0.0.1",
                "outcome": "success",
                "details": "Login",
            })
        insert_events(conn, events)

        cutoff = "2024-01-02T00:00:00Z"
        baseline = compute_baseline(conn, "user_01", cutoff)
        assert baseline["baseline_login_count"] == 10
        assert baseline["baseline_sufficient"] is False
    finally:
        conn.close()
        os.unlink(db_path)


def test_r1_unusual_hour_triggers():
    """R1 should trigger for login at hour with <=2% baseline logins."""
    conn, db_path = create_test_db()
    try:
        # 50 logins, all at hour 10 (so hour 10 has 50, others 0)
        base = datetime(2024, 1, 1, tzinfo=timezone.utc)
        events = []
        for i in range(50):
            ts = base.replace(hour=10, minute=i, second=0)
            events.append({
                "event_id": f"EVT-{i+1:06d}",
                "ts": ts.isoformat().replace("+00:00", "Z"),
                "user_id": "user_01",
                "event_type": "login",
                "device_id": "device_A",
                "resource": None,
                "source_ip": "10.0.0.1",
                "outcome": "success",
                "details": "Login",
            })
        insert_events(conn, events)

        # Add test event at hour 3 (0 baseline logins at hour 3)
        test_event = {
            "event_id": "EVT-999999",
            "ts": "2024-01-10T03:30:00Z",
            "user_id": "user_01",
            "event_type": "login",
            "device_id": "device_A",
            "resource": None,
            "source_ip": "10.0.0.1",
            "outcome": "success",
            "details": "Night login",
        }
        insert_events(conn, [test_event])

        cutoff = "2024-01-05T00:00:00Z"
        indicators = find_indicators(conn, "user_01", cutoff, "2024-01-10T00:00:00Z", "2024-01-10T23:59:59Z")

        r1_indicators = [i for i in indicators if i["rule"] == "R1_unusual_hour"]
        assert len(r1_indicators) == 1
        assert r1_indicators[0]["event_id"] == "EVT-999999"
    finally:
        conn.close()
        os.unlink(db_path)


def test_r1_no_trigger_when_baseline_insufficient():
    """R1 should not trigger when baseline_sufficient is False."""
    conn, db_path = create_test_db()
    try:
        # Only 10 logins at hour 10
        base = datetime(2024, 1, 1, tzinfo=timezone.utc)
        events = []
        for i in range(10):
            ts = base.replace(hour=10, minute=i*5, second=0)
            events.append({
                "event_id": f"EVT-{i+1:06d}",
                "ts": ts.isoformat().replace("+00:00", "Z"),
                "user_id": "user_01",
                "event_type": "login",
                "device_id": "device_A",
                "resource": None,
                "source_ip": "10.0.0.1",
                "outcome": "success",
                "details": "Login",
            })
        insert_events(conn, events)

        # Test event at hour 3
        test_event = {
            "event_id": "EVT-999999",
            "ts": "2024-01-10T03:30:00Z",
            "user_id": "user_01",
            "event_type": "login",
            "device_id": "device_A",
            "resource": None,
            "source_ip": "10.0.0.1",
            "outcome": "success",
            "details": "Night login",
        }
        insert_events(conn, [test_event])

        cutoff = "2024-01-05T00:00:00Z"
        indicators = find_indicators(conn, "user_01", cutoff, "2024-01-10T00:00:00Z", "2024-01-10T23:59:59Z")

        r1_indicators = [i for i in indicators if i["rule"] == "R1_unusual_hour"]
        assert len(r1_indicators) == 0
    finally:
        conn.close()
        os.unlink(db_path)


def test_r2_new_device_triggers():
    """R2 should trigger for device not seen in baseline."""
    conn, db_path = create_test_db()
    try:
        setup_baseline_events(conn)

        # Test event with new device
        test_event = {
            "event_id": "EVT-999999",
            "ts": "2024-01-10T10:00:00Z",
            "user_id": "user_01",
            "event_type": "login",
            "device_id": "device_NEW",
            "resource": None,
            "source_ip": "10.0.0.1",
            "outcome": "success",
            "details": "New device login",
        }
        insert_events(conn, [test_event])

        cutoff = "2024-01-02T00:00:00Z"
        indicators = find_indicators(conn, "user_01", cutoff, "2024-01-10T00:00:00Z", "2024-01-10T23:59:59Z")

        r2_indicators = [i for i in indicators if i["rule"] == "R2_new_device"]
        assert len(r2_indicators) == 1
        assert r2_indicators[0]["event_id"] == "EVT-999999"
    finally:
        conn.close()
        os.unlink(db_path)


def test_r3_rare_resource_triggers():
    """R3 should trigger for resource accessed <=1 time in baseline."""
    conn, db_path = create_test_db()
    try:
        setup_baseline_events(conn)  # email accessed 2x, github 2x, slack 1x

        # Test event with never-seen resource
        test_event = {
            "event_id": "EVT-999999",
            "ts": "2024-01-10T10:00:00Z",
            "user_id": "user_01",
            "event_type": "resource_access",
            "device_id": "device_A",
            "resource": "new_resource",
            "source_ip": "10.0.0.1",
            "outcome": "success",
            "details": "New resource",
        }
        insert_events(conn, [test_event])

        cutoff = "2024-01-02T00:00:00Z"
        indicators = find_indicators(conn, "user_01", cutoff, "2024-01-10T00:00:00Z", "2024-01-10T23:59:59Z")

        r3_indicators = [i for i in indicators if i["rule"] == "R3_rare_resource"]
        assert len(r3_indicators) == 1
        assert r3_indicators[0]["event_id"] == "EVT-999999"

        # Also test resource seen exactly once in baseline (slack)
        test_event2 = {
            "event_id": "EVT-999998",
            "ts": "2024-01-10T11:00:00Z",
            "user_id": "user_01",
            "event_type": "resource_access",
            "device_id": "device_A",
            "resource": "slack",
            "source_ip": "10.0.0.1",
            "outcome": "success",
            "details": "Slack again",
        }
        insert_events(conn, [test_event2])

        indicators2 = find_indicators(conn, "user_01", cutoff, "2024-01-10T00:00:00Z", "2024-01-10T23:59:59Z")
        r3_indicators2 = [i for i in indicators2 if i["rule"] == "R3_rare_resource" and i["event_id"] == "EVT-999998"]
        assert len(r3_indicators2) == 1
    finally:
        conn.close()
        os.unlink(db_path)


def test_r4_failure_burst_triggers():
    """R4 should trigger for 3+ failed logins in 10 minutes."""
    conn, db_path = create_test_db()
    try:
        setup_baseline_events(conn)

        # 3 failed logins within 5 minutes
        base = datetime(2024, 1, 10, 10, 0, 0, tzinfo=timezone.utc)
        events = []
        for i in range(3):
            ts = base + timedelta(minutes=i*2)
            events.append({
                "event_id": f"EVT-99999{i}",
                "ts": ts.isoformat().replace("+00:00", "Z"),
                "user_id": "user_01",
                "event_type": "login",
                "device_id": "device_A",
                "resource": None,
                "source_ip": "10.0.0.1",
                "outcome": "failure",
                "details": "Failed login",
            })
        insert_events(conn, events)

        cutoff = "2024-01-02T00:00:00Z"
        indicators = find_indicators(conn, "user_01", cutoff, "2024-01-10T00:00:00Z", "2024-01-10T23:59:59Z")

        r4_indicators = [i for i in indicators if i["rule"] == "R4_failure_burst"]
        assert len(r4_indicators) == 3  # All 3 events in the burst
    finally:
        conn.close()
        os.unlink(db_path)


def test_r4_no_trigger_spread_over_hour():
    """R4 should NOT trigger for 3 failed logins spread over an hour."""
    conn, db_path = create_test_db()
    try:
        setup_baseline_events(conn)

        # 3 failed logins spread over 60 minutes
        base = datetime(2024, 1, 10, 10, 0, 0, tzinfo=timezone.utc)
        events = []
        for i in range(3):
            ts = base + timedelta(minutes=i*30)
            events.append({
                "event_id": f"EVT-99999{i}",
                "ts": ts.isoformat().replace("+00:00", "Z"),
                "user_id": "user_01",
                "event_type": "login",
                "device_id": "device_A",
                "resource": None,
                "source_ip": "10.0.0.1",
                "outcome": "failure",
                "details": "Failed login",
            })
        insert_events(conn, events)

        cutoff = "2024-01-02T00:00:00Z"
        indicators = find_indicators(conn, "user_01", cutoff, "2024-01-10T00:00:00Z", "2024-01-10T23:59:59Z")

        r4_indicators = [i for i in indicators if i["rule"] == "R4_failure_burst"]
        assert len(r4_indicators) == 0
    finally:
        conn.close()
        os.unlink(db_path)


def test_normal_event_no_indicators():
    """Normal event on usual device in usual hours should trigger nothing."""
    conn, db_path = create_test_db()
    try:
        setup_baseline_events(conn)

        # Normal event: usual device, work hour, common resource
        test_event = {
            "event_id": "EVT-999999",
            "ts": "2024-01-10T10:00:00Z",
            "user_id": "user_01",
            "event_type": "resource_access",
            "device_id": "device_A",
            "resource": "email",
            "source_ip": "10.0.0.1",
            "outcome": "success",
            "details": "Normal access",
        }
        insert_events(conn, [test_event])

        cutoff = "2024-01-02T00:00:00Z"
        indicators = find_indicators(conn, "user_01", cutoff, "2024-01-10T00:00:00Z", "2024-01-10T23:59:59Z")

        assert len(indicators) == 0
    finally:
        conn.close()
        os.unlink(db_path)


def test_planted_event_triggers_r1_r2_r3():
    """A planted event (new device + 03:00 UTC + never-used resource) triggers R1, R2, R3."""
    conn, db_path = create_test_db()
    try:
        # Baseline: 30 logins at hour 10, device_A, resources email/github
        base = datetime(2024, 1, 1, tzinfo=timezone.utc)
        events = []
        for i in range(30):
            ts = base.replace(hour=10, minute=i, second=0)
            events.append({
                "event_id": f"EVT-{i+1:06d}",
                "ts": ts.isoformat().replace("+00:00", "Z"),
                "user_id": "user_01",
                "event_type": "login",
                "device_id": "device_A",
                "resource": None,
                "source_ip": "10.0.0.1",
                "outcome": "success",
                "details": "Login",
            })
        # Some resource accesses
        for res in ["email", "github"]:
            ts = base.replace(hour=11, minute=0, second=0)
            events.append({
                "event_id": f"EVT-{100+len(events):06d}",
                "ts": ts.isoformat().replace("+00:00", "Z"),
                "user_id": "user_01",
                "event_type": "resource_access",
                "device_id": "device_A",
                "resource": res,
                "source_ip": "10.0.0.1",
                "outcome": "success",
                "details": f"Access {res}",
            })
        insert_events(conn, events)

        # Planted event: new device, 03:00 UTC, never-used resource, LOGIN type (R1 only checks logins)
        test_event = {
            "event_id": "EVT-999999",
            "ts": "2024-01-10T03:00:00Z",
            "user_id": "user_01",
            "event_type": "login",  # R1 only triggers for logins
            "device_id": "device_NEW",
            "resource": "never_used_resource",
            "source_ip": "10.0.0.1",
            "outcome": "success",
            "details": "Suspicious login",
        }
        insert_events(conn, [test_event])

        cutoff = "2024-01-05T00:00:00Z"
        indicators = find_indicators(conn, "user_01", cutoff, "2024-01-10T00:00:00Z", "2024-01-10T23:59:59Z")

        rules = {i["rule"] for i in indicators}
        assert "R1_unusual_hour" in rules
        assert "R2_new_device" in rules
        assert "R3_rare_resource" in rules
        assert len(indicators) == 3
    finally:
        conn.close()
        os.unlink(db_path)


def test_known_devices_tracking():
    """Known devices should track first_seen, last_seen, count."""
    conn, db_path = create_test_db()
    try:
        base = datetime(2024, 1, 1, tzinfo=timezone.utc)
        events = [
            {
                "event_id": "EVT-000001",
                "ts": "2024-01-01T10:00:00Z",
                "user_id": "user_01",
                "event_type": "login",
                "device_id": "device_A",
                "resource": None,
                "source_ip": "10.0.0.1",
                "outcome": "success",
                "details": "Login",
            },
            {
                "event_id": "EVT-000002",
                "ts": "2024-01-02T10:00:00Z",
                "user_id": "user_01",
                "event_type": "login",
                "device_id": "device_A",
                "resource": None,
                "source_ip": "10.0.0.1",
                "outcome": "success",
                "details": "Login",
            },
            {
                "event_id": "EVT-000003",
                "ts": "2024-01-01T11:00:00Z",
                "user_id": "user_01",
                "event_type": "resource_access",
                "device_id": "device_B",
                "resource": "email",
                "source_ip": "10.0.0.1",
                "outcome": "success",
                "details": "Access",
            },
        ]
        insert_events(conn, events)

        cutoff = "2024-01-05T00:00:00Z"
        baseline = compute_baseline(conn, "user_01", cutoff)

        assert len(baseline["known_devices"]) == 2
        dev_a = next(d for d in baseline["known_devices"] if d["device_id"] == "device_A")
        dev_b = next(d for d in baseline["known_devices"] if d["device_id"] == "device_B")
        assert dev_a["count"] == 2
        assert dev_b["count"] == 1
        assert dev_a["first_seen"] == "2024-01-01T10:00:00Z"
        assert dev_a["last_seen"] == "2024-01-02T10:00:00Z"
    finally:
        conn.close()
        os.unlink(db_path)


if __name__ == "__main__":
    test_baseline_sufficient_true()
    test_baseline_sufficient_false()
    test_r1_unusual_hour_triggers()
    test_r1_no_trigger_when_baseline_insufficient()
    test_r2_new_device_triggers()
    test_r3_rare_resource_triggers()
    test_r4_failure_burst_triggers()
    test_r4_no_trigger_spread_over_hour()
    test_normal_event_no_indicators()
    test_planted_event_triggers_r1_r2_r3()
    test_known_devices_tracking()
    print("All test_baseline.py tests passed!")