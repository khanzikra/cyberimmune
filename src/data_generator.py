"""
Deterministic synthetic data generator for CyberImmune.
Generates 10 users x 30 days of events following SPEC.md section 2.
"""
import random
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
from pathlib import Path
import argparse

from .database import connect, create_schema, insert_events, insert_context


USERS = [f"user_{i:02d}" for i in range(1, 11)]
EVENT_TYPES = ("login", "resource_access", "password_reset", "mfa_challenge")
OUTCOMES = ("success", "failure")
RECORD_TYPES = ("it_ticket", "approved_device", "travel_notice", "hr_note")

# Resources pool
RESOURCES = [
    "github", "jira", "confluence", "slack", "gdrive", "aws_console",
    "datadog", "pagerduty", "vpn", "database", "k8s_cluster", "ci_cd",
    "wiki", "notion", "figma", "linear", "vercel", "cloudflare"
]

# Details templates (short, plain, harmless)
LOGIN_DETAILS = [
    "User logged in", "Successful login", "Authentication succeeded",
    "Signed in via SSO", "Password accepted", "MFA approved"
]
RESOURCE_DETAILS = [
    "Accessed resource", "Viewed dashboard", "Downloaded report",
    "Checked status", "Reviewed logs", "Updated config"
]
FAILURE_DETAILS = [
    "Invalid password", "MFA code expired", "Account locked",
    "Wrong credentials", "Token expired", "IP not allowed"
]


def generate_user_profile(rng: random.Random, user_id: str) -> Dict[str, Any]:
    """Generate a user's profile: usual devices, working hours, common resources."""
    # 1-2 usual devices
    num_devices = rng.randint(1, 2)
    devices = [f"device_{user_id}_{chr(ord('a') + i)}" for i in range(num_devices)]

    # Working hours: start 7-10, end 16-19 (local, converted to UTC roughly)
    # For simplicity, use UTC hours directly: start 7-10, end 16-19
    work_start = rng.randint(7, 10)
    work_end = rng.randint(16, 19)

    # 4-8 regularly used resources
    num_resources = rng.randint(4, 8)
    regular_resources = rng.sample(RESOURCES, num_resources)

    # 2 users have legit night-time patterns (users 03 and 07)
    night_worker = user_id in ("user_03", "user_07")

    return {
        "devices": devices,
        "work_start": work_start,
        "work_end": work_end,
        "regular_resources": regular_resources,
        "night_worker": night_worker,
    }


def generate_events_for_user(
    rng: random.Random,
    user_id: str,
    profile: Dict[str, Any],
    start_date: datetime,
    days: int = 30,
    event_counter_start: int = 1
) -> tuple[List[Dict[str, Any]], int]:
    """Generate events for one user over N days. Returns (events, next_event_counter)."""
    events = []
    event_counter = event_counter_start
    devices = profile["devices"]
    work_start = profile["work_start"]
    work_end = profile["work_end"]
    regular_resources = profile["regular_resources"]
    night_worker = profile["night_worker"]

    for day in range(days):
        current_date = start_date + timedelta(days=day)
        is_weekend = current_date.weekday() >= 5

        # Events per day: 8-15 on weekdays, fewer on weekends
        if is_weekend:
            num_events = rng.randint(2, 6)
        else:
            num_events = rng.randint(8, 15)

        for _ in range(num_events):
            # Pick hour
            if night_worker and rng.random() < 0.3:
                # Night worker sometimes works at night (22-05)
                hour = rng.randint(22, 23) if rng.random() < 0.5 else rng.randint(0, 5)
            else:
                # Normal working hours
                hour = rng.randint(work_start, work_end - 1)

            minute = rng.randint(0, 59)
            second = rng.randint(0, 59)
            ts = current_date.replace(hour=hour, minute=minute, second=second, tzinfo=timezone.utc)

            # Pick event type (mostly logins and resource_access)
            event_type = rng.choices(
                EVENT_TYPES,
                weights=[0.45, 0.40, 0.10, 0.05],
                k=1
            )[0]

            device_id = rng.choice(devices)
            source_ip = f"10.0.{rng.randint(0, 255)}.{rng.randint(1, 254)}"

            if event_type == "login":
                outcome = rng.choices(OUTCOMES, weights=[0.95, 0.05], k=1)[0]
                resource = None
                details = rng.choice(LOGIN_DETAILS if outcome == "success" else FAILURE_DETAILS)

            elif event_type == "resource_access":
                outcome = "success"
                # Mostly regular resources, occasionally others
                if rng.random() < 0.85:
                    resource = rng.choice(regular_resources)
                else:
                    resource = rng.choice(RESOURCES)
                details = rng.choice(RESOURCE_DETAILS)

            elif event_type == "password_reset":
                outcome = rng.choices(OUTCOMES, weights=[0.9, 0.1], k=1)[0]
                resource = None
                details = "Password reset requested" if outcome == "success" else "Reset link expired"

            else:  # mfa_challenge
                outcome = rng.choices(OUTCOMES, weights=[0.97, 0.03], k=1)[0]
                resource = None
                details = "MFA challenge completed" if outcome == "success" else "MFA code rejected"

            event_id = f"EVT-{event_counter:06d}"
            event_counter += 1

            events.append({
                "event_id": event_id,
                "ts": ts.isoformat().replace("+00:00", "Z"),
                "user_id": user_id,
                "event_type": event_type,
                "device_id": device_id,
                "resource": resource,
                "source_ip": source_ip,
                "outcome": outcome,
                "details": details,
            })

    return events, event_counter


def generate_context_records(
    rng: random.Random,
    users: List[str],
    profiles: Dict[str, Dict],
    start_date: datetime,
    days: int = 30
) -> List[Dict[str, Any]]:
    """Generate context records (IT tickets, approved devices, etc.)."""
    records = []
    record_counter = 1

    for user_id in users:
        profile = profiles[user_id]
        devices = profile["devices"]

        # 1-3 approved device records
        for device in devices:
            if rng.random() < 0.8:
                ts = start_date + timedelta(days=rng.randint(-30, -1))
                records.append({
                    "record_id": f"CTX-{record_counter:04d}",
                    "ts": ts.isoformat().replace("+00:00", "Z"),
                    "user_id": user_id,
                    "record_type": "approved_device",
                    "device_id": device,
                    "summary": f"Device {device} approved for {user_id}",
                    "status": "active",
                })
                record_counter += 1

        # 0-2 IT tickets
        for _ in range(rng.randint(0, 2)):
            ts = start_date + timedelta(days=rng.randint(0, days - 1))
            ticket_type = rng.choice(["laptop_replacement", "password_reset", "access_request", "vpn_issue"])
            records.append({
                "record_id": f"CTX-{record_counter:04d}",
                "ts": ts.isoformat().replace("+00:00", "Z"),
                "user_id": user_id,
                "record_type": "it_ticket",
                "device_id": rng.choice(devices) if rng.random() < 0.5 else None,
                "summary": f"IT ticket: {ticket_type} for {user_id}",
                "status": rng.choice(["open", "resolved", "closed"]),
            })
            record_counter += 1

        # 0-1 travel notices (mostly for night workers)
        if profile["night_worker"] and rng.random() < 0.5:
            ts = start_date + timedelta(days=rng.randint(0, days - 1))
            records.append({
                "record_id": f"CTX-{record_counter:04d}",
                "ts": ts.isoformat().replace("+00:00", "Z"),
                "user_id": user_id,
                "record_type": "travel_notice",
                "device_id": None,
                "summary": f"Travel notice: {user_id} working remotely",
                "status": "active",
            })
            record_counter += 1

        # 0-1 HR notes
        if rng.random() < 0.3:
            ts = start_date + timedelta(days=rng.randint(0, days - 1))
            records.append({
                "record_id": f"CTX-{record_counter:04d}",
                "ts": ts.isoformat().replace("+00:00", "Z"),
                "user_id": user_id,
                "record_type": "hr_note",
                "device_id": None,
                "summary": f"HR note: {user_id} schedule change",
                "status": "active",
            })
            record_counter += 1

    return records


def generate_history(seed: int = 42) -> Dict[str, Any]:
    """
    Generate full synthetic history.
    Returns dict with 'events', 'context_records', 'profiles'.
    """
    rng = random.Random(seed)
    start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)  # Fixed start date

    profiles = {u: generate_user_profile(rng, u) for u in USERS}

    all_events = []
    event_counter = 1
    for user_id in USERS:
        user_events, event_counter = generate_events_for_user(
            rng, user_id, profiles[user_id], start_date, 30, event_counter
        )
        all_events.extend(user_events)

    # Sort by timestamp then event_id
    all_events.sort(key=lambda e: (e["ts"], e["event_id"]))

    context_records = generate_context_records(rng, USERS, profiles, start_date, 30)
    context_records.sort(key=lambda r: (r["ts"], r["record_id"]))

    return {
        "events": all_events,
        "context_records": context_records,
        "profiles": profiles,
    }


def write_db(db_path: str, seed: int = 42) -> None:
    """Generate history and write to SQLite database."""
    data = generate_history(seed)

    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = connect(db_path)
    create_schema(conn)

    insert_events(conn, data["events"])
    insert_context(conn, data["context_records"])

    conn.commit()

    # Print stats
    cur = conn.execute("SELECT user_id, COUNT(*) as cnt FROM events GROUP BY user_id ORDER BY user_id")
    print("Events per user:")
    for row in cur:
        print(f"  {row['user_id']}: {row['cnt']}")

    cur = conn.execute("SELECT user_id, COUNT(*) as cnt FROM context_records GROUP BY user_id ORDER BY user_id")
    print("\nContext records per user:")
    for row in cur:
        print(f"  {row['user_id']}: {row['cnt']}")

    cur = conn.execute("SELECT COUNT(*) as cnt FROM events")
    print(f"\nTotal events: {cur.fetchone()['cnt']}")
    cur = conn.execute("SELECT COUNT(*) as cnt FROM context_records")
    print(f"Total context records: {cur.fetchone()['cnt']}")

    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate synthetic CyberImmune data")
    parser.add_argument("--db", default="data/history.db", help="Output database path")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    write_db(args.db, args.seed)