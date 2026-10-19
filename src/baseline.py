"""
Baseline computation and indicator detection for CyberImmune.
Implements the four rules from SPEC.md section 3.
"""
import sqlite3
from .database import connect
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from collections import Counter, defaultdict


def compute_baseline(
    conn: sqlite3.Connection,
    user_id: str,
    cutoff: str
) -> Dict[str, Any]:
    """
    Compute baseline for a user using events before cutoff.
    Returns dict matching SPEC.md get_baseline output.
    """
    # Get all login events before cutoff
    cur = conn.execute("""
        SELECT ts, device_id, resource
        FROM events
        WHERE user_id = ? AND event_type = 'login' AND ts < ?
        ORDER BY ts
    """, (user_id, cutoff))
    logins = cur.fetchall()

    baseline_login_count = len(logins)
    baseline_sufficient = baseline_login_count >= 20

    if baseline_login_count == 0:
        return {
            "baseline_login_count": 0,
            "baseline_sufficient": False,
            "login_hour_histogram": [0] * 24,
            "known_devices": [],
            "top_resources": [],
            "avg_events_per_day": 0.0,
            "cutoff": cutoff,
        }

    # Login hour histogram (UTC)
    hour_hist = [0] * 24
    for row in logins:
        dt = datetime.fromisoformat(row["ts"].replace("Z", "+00:00"))
        hour_hist[dt.hour] += 1

    # Known devices with first/last seen and count
    device_stats = defaultdict(lambda: {"first_seen": None, "last_seen": None, "count": 0})
    for row in logins:
        dev = row["device_id"]
        ts = row["ts"]
        stats = device_stats[dev]
        stats["count"] += 1
        if stats["first_seen"] is None or ts < stats["first_seen"]:
            stats["first_seen"] = ts
        if stats["last_seen"] is None or ts > stats["last_seen"]:
            stats["last_seen"] = ts

    known_devices = [
        {
            "device_id": dev,
            "first_seen": stats["first_seen"],
            "last_seen": stats["last_seen"],
            "count": stats["count"],
        }
        for dev, stats in device_stats.items()
    ]
    known_devices.sort(key=lambda d: d["first_seen"])

    # Top 10 resources accessed (all event types)
    cur = conn.execute("""
        SELECT resource, COUNT(*) as cnt
        FROM events
        WHERE user_id = ? AND ts < ? AND resource IS NOT NULL
        GROUP BY resource
        ORDER BY cnt DESC
        LIMIT 10
    """, (user_id, cutoff))
    top_resources = [{"resource": row["resource"], "count": row["cnt"]} for row in cur.fetchall()]

    # Average events per day (all event types)
    cur = conn.execute("""
        SELECT COUNT(*) as cnt, MIN(ts) as min_ts, MAX(ts) as max_ts
        FROM events
        WHERE user_id = ? AND ts < ?
    """, (user_id, cutoff))
    row = cur.fetchone()
    if row["cnt"] > 0 and row["min_ts"] and row["max_ts"]:
        min_dt = datetime.fromisoformat(row["min_ts"].replace("Z", "+00:00"))
        max_dt = datetime.fromisoformat(row["max_ts"].replace("Z", "+00:00"))
        day_span = max(1, (max_dt - min_dt).days + 1)
        avg_events_per_day = row["cnt"] / day_span
    else:
        avg_events_per_day = 0.0

    return {
        "baseline_login_count": baseline_login_count,
        "baseline_sufficient": baseline_sufficient,
        "login_hour_histogram": hour_hist,
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
    Find indicators (R1-R4) for events in the focus window.
    Returns list of {rule, event_id, detail}.
    """
    indicators = []

    # Get baseline for R1 and R2
    baseline = compute_baseline(conn, user_id, cutoff)
    baseline_login_count = baseline["baseline_login_count"]
    baseline_sufficient = baseline["baseline_sufficient"]
    hour_hist = baseline["login_hour_histogram"]
    known_device_ids = {d["device_id"] for d in baseline["known_devices"]}
    resource_counts = {r["resource"]: r["count"] for r in baseline["top_resources"]}
    # Also get resources not in top 10 but accessed before
    cur = conn.execute("""
        SELECT resource, COUNT(*) as cnt
        FROM events
        WHERE user_id = ? AND ts < ? AND resource IS NOT NULL
        GROUP BY resource
    """, (user_id, cutoff))
    for row in cur.fetchall():
        if row["resource"] not in resource_counts:
            resource_counts[row["resource"]] = row["cnt"]

    # Get events in focus window
    cur = conn.execute("""
        SELECT event_id, ts, event_type, device_id, resource, outcome
        FROM events
        WHERE user_id = ? AND ts >= ? AND ts <= ?
        ORDER BY ts, event_id
    """, (user_id, window_start, window_end))
    focus_events = cur.fetchall()

    # R1: unusual_hour - user's baseline logins in same UTC hour <= 2% of baseline logins
    if baseline_sufficient:
        for event in focus_events:
            if event["event_type"] == "login":
                dt = datetime.fromisoformat(event["ts"].replace("Z", "+00:00"))
                hour_count = hour_hist[dt.hour]
                if hour_count / baseline_login_count <= 0.02:
                    indicators.append({
                        "rule": "R1",
                        "event_id": event["event_id"],
                        "detail": f"Login at hour {dt.hour}:00 UTC (only {hour_count}/{baseline_login_count} baseline logins in this hour)"
                    })

    # R2: new_device - device_id never seen for this user before cutoff
    for event in focus_events:
        if event["device_id"] and event["device_id"] not in known_device_ids:
            indicators.append({
                "rule": "R2",
                "event_id": event["event_id"],
                "detail": f"New device '{event['device_id']}' not seen in baseline"
            })

    # R3: rare_resource - resource accessed <= 1 time by this user before cutoff
    for event in focus_events:
        if event["resource"]:
            count = resource_counts.get(event["resource"], 0)
            if count <= 1:
                indicators.append({
                    "rule": "R3",
                    "event_id": event["event_id"],
                    "detail": f"Resource '{event['resource']}' accessed {count} time(s) in baseline"
                })

    # R4: failure_burst - >= 3 failed logins by user inside any 10-minute window
    failed_logins = [
        e for e in focus_events
        if e["event_type"] == "login" and e["outcome"] == "failure"
    ]
    # Sort by timestamp
    failed_logins.sort(key=lambda e: e["ts"])

    for i in range(len(failed_logins)):
        window_start_dt = datetime.fromisoformat(failed_logins[i]["ts"].replace("Z", "+00:00"))
        window_end_dt = window_start_dt + timedelta(minutes=10)
        count = 1
        for j in range(i + 1, len(failed_logins)):
            event_dt = datetime.fromisoformat(failed_logins[j]["ts"].replace("Z", "+00:00"))
            if event_dt <= window_end_dt:
                count += 1
            else:
                break
        if count >= 3:
            event_ids = [failed_logins[k]["event_id"] for k in range(i, i + count)]
            indicators.append({
                "rule": "R4",
                "event_id": event_ids[0],
                "detail": f"{count} failed logins in 10 minutes: {', '.join(event_ids)}"
            })
            break  # Only report first burst

    return indicators


# Need to import timedelta
from datetime import timedelta