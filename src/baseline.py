"""
Baseline computation and anomaly indicator detection for CyberImmune.
Implements the four deterministic rules from SPEC.md section 3.
"""
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional
from collections import defaultdict

from src.database import connect


def compute_baseline(
    conn: sqlite3.Connection,
    user_id: str,
    cutoff: str
) -> Dict[str, Any]:
    """
    Compute baseline statistics for a user based on events before cutoff.
    Returns dict matching get_baseline schema in SPEC.md.
    """
    cursor = conn.cursor()

    # Get baseline events (ts < cutoff)
    cursor.execute("""
        SELECT * FROM events
        WHERE user_id = ? AND ts < ?
        ORDER BY ts
    """, (user_id, cutoff))
    baseline_events = [dict(row) for row in cursor.fetchall()]

    # Filter to logins for login-specific stats
    baseline_logins = [e for e in baseline_events if e["event_type"] == "login"]
    baseline_login_count = len(baseline_logins)
    baseline_sufficient = baseline_login_count >= 20

    # Login hour histogram (24 hours)
    login_hour_histogram = [0] * 24
    for e in baseline_logins:
        ts = datetime.fromisoformat(e["ts"].replace("Z", "+00:00"))
        login_hour_histogram[ts.hour] += 1

    # Known devices with first/last seen and count
    device_stats = defaultdict(lambda: {"first_seen": None, "last_seen": None, "count": 0})
    for e in baseline_events:
        dev = e["device_id"]
        ts = e["ts"]
        stats = device_stats[dev]
        stats["count"] += 1
        if stats["first_seen"] is None or ts < stats["first_seen"]:
            stats["first_seen"] = ts
        if stats["last_seen"] is None or ts > stats["last_seen"]:
            stats["last_seen"] = ts

    known_devices = [
        {"device_id": dev, **stats}
        for dev, stats in device_stats.items()
    ]
    known_devices.sort(key=lambda d: d["first_seen"])

    # Top resources (top 10 by count)
    resource_counts = defaultdict(int)
    for e in baseline_events:
        if e["resource"]:
            resource_counts[e["resource"]] += 1
    top_resources = [
        {"resource": res, "count": cnt}
        for res, cnt in sorted(resource_counts.items(), key=lambda x: -x[1])[:10]
    ]

    # Average events per day
    if baseline_events:
        first_ts = datetime.fromisoformat(baseline_events[0]["ts"].replace("Z", "+00:00"))
        last_ts = datetime.fromisoformat(baseline_events[-1]["ts"].replace("Z", "+00:00"))
        day_span = max(1, (last_ts - first_ts).days + 1)
        avg_events_per_day = len(baseline_events) / day_span
    else:
        avg_events_per_day = 0.0

    return {
        "baseline_login_count": baseline_login_count,
        "baseline_sufficient": baseline_sufficient,
        "login_hour_histogram": login_hour_histogram,
        "known_devices": known_devices,
        "top_resources": top_resources,
        "avg_events_per_day": round(avg_events_per_day, 2),
        "cutoff": cutoff,
    }


def find_indicators(
    conn: sqlite3.Connection,
    user_id: str,
    cutoff: str,
    window_start: str,
    window_end: str
) -> List[Dict[str, Any]]:
    """
    Find anomaly indicators for events in [window_start, window_end] for a user.
    Returns list of {rule, event_id, detail} for R1-R4.
    """
    cursor = conn.cursor()

    # Get baseline stats
    baseline = compute_baseline(conn, user_id, cutoff)
    baseline_login_count = baseline["baseline_login_count"]
    baseline_sufficient = baseline["baseline_sufficient"]
    login_hour_histogram = baseline["login_hour_histogram"]
    known_devices = {d["device_id"] for d in baseline["known_devices"]}

    # Resource counts in baseline
    resource_counts = defaultdict(int)
    cursor.execute("""
        SELECT resource FROM events
        WHERE user_id = ? AND ts < ? AND resource IS NOT NULL
    """, (user_id, cutoff))
    for row in cursor.fetchall():
        resource_counts[row["resource"]] += 1

    # Get events in window
    cursor.execute("""
        SELECT * FROM events
        WHERE user_id = ? AND ts >= ? AND ts <= ?
        ORDER BY ts
    """, (user_id, window_start, window_end))
    window_events = [dict(row) for row in cursor.fetchall()]

    indicators = []

    for event in window_events:
        event_id = event["event_id"]
        ts = datetime.fromisoformat(event["ts"].replace("Z", "+00:00"))
        hour = ts.hour
        device_id = event["device_id"]
        resource = event["resource"]
        event_type = event["event_type"]
        outcome = event["outcome"]

        # R1: unusual_hour - only for logins, only if baseline_sufficient
        if event_type == "login" and baseline_sufficient:
            hour_logins = login_hour_histogram[hour]
            if hour_logins <= 0.02 * baseline_login_count:
                indicators.append({
                    "rule": "R1_unusual_hour",
                    "event_id": event_id,
                    "detail": f"Login at {hour:02d}:00 UTC (only {hour_logins}/{baseline_login_count} baseline logins in this hour)"
                })

        # R2: new_device
        if device_id not in known_devices:
            indicators.append({
                "rule": "R2_new_device",
                "event_id": event_id,
                "detail": f"Device {device_id} not seen in baseline"
            })

        # R3: rare_resource
        if resource and resource_counts.get(resource, 0) <= 1:
            indicators.append({
                "rule": "R3_rare_resource",
                "event_id": event_id,
                "detail": f"Resource {resource} accessed {resource_counts.get(resource, 0)} time(s) in baseline"
            })

    # R4: failure_burst - check all failed logins in window for user
    failed_logins = [
        e for e in window_events
        if e["event_type"] == "login" and e["outcome"] == "failure"
    ]

    # Sort by timestamp
    failed_logins.sort(key=lambda e: e["ts"])

    # Check for 3+ failed logins in any 10-minute window
    for i in range(len(failed_logins)):
        window_end_time = datetime.fromisoformat(failed_logins[i]["ts"].replace("Z", "+00:00"))
        window_start_time = window_end_time - timedelta(minutes=10)

        # Count failed logins in this 10-minute window
        count = sum(1 for e in failed_logins
                    if window_start_time <= datetime.fromisoformat(e["ts"].replace("Z", "+00:00")) <= window_end_time)

        if count >= 3:
            # Create indicator for each event in this burst
            for e in failed_logins:
                e_ts = datetime.fromisoformat(e["ts"].replace("Z", "+00:00"))
                if window_start_time <= e_ts <= window_end_time:
                    # Check if already added
                    existing = any(ind["event_id"] == e["event_id"] and ind["rule"] == "R4_failure_burst"
                                   for ind in indicators)
                    if not existing:
                        indicators.append({
                            "rule": "R4_failure_burst",
                            "event_id": e["event_id"],
                            "detail": f"{count} failed logins in 10-minute window ending {window_end_time.isoformat()}"
                        })

    return indicators


if __name__ == "__main__":
    import sys
    from database import connect

    if len(sys.argv) < 4:
        print("Usage: python -m src.baseline <db> <user_id> <cutoff> [window_start] [window_end]")
        sys.exit(1)

    db_path = sys.argv[1]
    user_id = sys.argv[2]
    cutoff = sys.argv[3]
    window_start = sys.argv[4] if len(sys.argv) > 4 else cutoff
    window_end = sys.argv[5] if len(sys.argv) > 5 else cutoff

    conn = connect(db_path)
    baseline = compute_baseline(conn, user_id, cutoff)
    print("Baseline:")
    for k, v in baseline.items():
        if k not in ("known_devices", "top_resources", "login_hour_histogram"):
            print(f"  {k}: {v}")
    print(f"  known_devices: {len(baseline['known_devices'])} devices")
    print(f"  top_resources: {baseline['top_resources'][:5]}...")

    indicators = find_indicators(conn, user_id, cutoff, window_start, window_end)
    print(f"\nIndicators ({len(indicators)}):")
    for ind in indicators:
        print(f"  {ind['rule']}: {ind['event_id']} - {ind['detail']}")

    conn.close()