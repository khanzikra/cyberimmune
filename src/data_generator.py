"""
Deterministic synthetic data generator for CyberImmune.
Generates 10 users x 30 days of events with specific patterns.
"""
import random
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
from pathlib import Path
import argparse

from src.database import connect, create_schema, insert_events, insert_context


# Constants
USERS = [f"user_{i:02d}" for i in range(1, 11)]
EVENT_TYPES = ["login", "resource_access", "password_reset", "mfa_challenge"]
OUTCOMES = ["success", "failure"]
RESOURCE_POOL = [
    "email", "vpn", "github", "jira", "confluence", "slack", "aws_console",
    "gcp_console", "azure_portal", "datadog", "pagerduty", "salesforce",
    "workday", "bamboohr", "office365", "zoom", "teams", "notion"
]
RECORD_TYPES = ["it_ticket", "approved_device", "travel_notice", "hr_note"]


def generate_user_profile(rng: random.Random, user_id: str) -> Dict[str, Any]:
    """Generate a user's baseline profile: devices, working hours, common resources."""
    # 1-2 usual devices
    num_devices = rng.randint(1, 2)
    devices = [f"device_{user_id}_{i}" for i in range(1, num_devices + 1)]

    # Working hours: start 7-10, end 16-19 (UTC)
    work_start = rng.randint(7, 10)
    work_end = rng.randint(16, 19)

    # 4-8 regularly used resources
    num_resources = rng.randint(4, 8)
    common_resources = rng.sample(RESOURCE_POOL, num_resources)

    # Night-time worker flag (2 users)
    is_night_worker = user_id in ("user_03", "user_07")

    return {
        "user_id": user_id,
        "devices": devices,
        "work_start": work_start,
        "work_end": work_end,
        "common_resources": common_resources,
        "is_night_worker": is_night_worker,
    }


def is_work_hour(profile: Dict[str, Any], hour: int) -> bool:
    """Check if an hour is within user's working hours."""
    if profile["is_night_worker"]:
        # Night workers: 22:00-06:00 UTC
        return hour >= 22 or hour < 6
    return profile["work_start"] <= hour < profile["work_end"]


def generate_events_for_day(
    rng: random.Random,
    profile: Dict[str, Any],
    day_offset: int,
    base_date: datetime,
    event_id_counter: List[int]
) -> List[Dict[str, Any]]:
    """Generate events for a single user on a single day."""
    events = []
    user_id = profile["user_id"]
    current_date = base_date + timedelta(days=day_offset)

    # Skip weekends for most users (80% chance)
    if current_date.weekday() >= 5 and not profile["is_night_worker"] and rng.random() < 0.8:
        return events

    # Number of events: 8-15 per day
    num_events = rng.randint(8, 15)

    for _ in range(num_events):
        # Pick hour weighted toward work hours
        if rng.random() < 0.85:
            # Work hour
            if profile["is_night_worker"]:
                hour = rng.choice(list(range(22, 24)) + list(range(0, 6)))
            else:
                hour = rng.randint(profile["work_start"], profile["work_end"] - 1)
        else:
            # Off hour
            hour = rng.randint(0, 23)

        minute = rng.randint(0, 59)
        second = rng.randint(0, 59)
        ts = current_date.replace(hour=hour, minute=minute, second=second, tzinfo=timezone.utc)

        event_id_counter[0] += 1
        event_id = f"EVT-{event_id_counter[0]:06d}"

        # Pick device: usually one of their devices
        if rng.random() < 0.95:
            device_id = rng.choice(profile["devices"])
        else:
            # Occasionally a new device (but not in baseline period for this simulation)
            device_id = f"device_{user_id}_new_{rng.randint(1000, 9999)}"

        # Pick event type: mostly logins and resource_access
        event_type = rng.choices(
            EVENT_TYPES,
            weights=[0.5, 0.4, 0.05, 0.05]
        )[0]

        # Resource for resource_access
        resource = None
        if event_type == "resource_access":
            if rng.random() < 0.8:
                resource = rng.choice(profile["common_resources"])
            else:
                resource = rng.choice(RESOURCE_POOL)

        # Outcome: mostly success
        outcome = rng.choices(OUTCOMES, weights=[0.95, 0.05])[0]

        # Details (short, harmless)
        detail_templates = {
            "login": ["User logged in", "Successful login", "Login from known device"],
            "resource_access": ["Accessed resource", "Viewed dashboard", "Downloaded report"],
            "password_reset": ["Password reset requested", "Password changed successfully"],
            "mfa_challenge": ["MFA challenge completed", "Push notification approved"],
        }
        details = rng.choice(detail_templates.get(event_type, ["Event recorded"]))

        events.append({
            "event_id": event_id,
            "ts": ts.isoformat().replace("+00:00", "Z"),
            "user_id": user_id,
            "event_type": event_type,
            "device_id": device_id,
            "resource": resource,
            "source_ip": f"10.0.{rng.randint(0, 255)}.{rng.randint(1, 254)}",
            "outcome": outcome,
            "details": details,
        })

    return events


def generate_history(seed: int = 42) -> List[Dict[str, Any]]:
    """
    Generate full 30-day history for all 10 users.
    Returns list of event dicts.
    """
    rng = random.Random(seed)
    base_date = datetime(2024, 1, 1, tzinfo=timezone.utc)

    # Generate profiles for all users
    profiles = {u: generate_user_profile(rng, u) for u in USERS}

    all_events = []
    event_id_counter = [0]

    for user_id in USERS:
        profile = profiles[user_id]
        for day in range(30):
            day_events = generate_events_for_day(rng, profile, day, base_date, event_id_counter)
            all_events.extend(day_events)

    # Sort by timestamp then event_id
    all_events.sort(key=lambda e: (e["ts"], e["event_id"]))
    return all_events


def generate_context_records(rng: random.Random, profiles: Dict[str, Dict]) -> List[Dict[str, Any]]:
    """Generate some context records (IT tickets, approved devices, etc.)."""
    records = []
    record_id_counter = 0

    for user_id, profile in profiles.items():
        # Each user gets 1-3 context records
        num_records = rng.randint(1, 3)
        for _ in range(num_records):
            record_id_counter += 1
            record_type = rng.choice(RECORD_TYPES)

            if record_type == "approved_device":
                device_id = rng.choice(profile["devices"])
                summary = f"Device {device_id} approved for {user_id}"
                status = "approved"
            elif record_type == "it_ticket":
                device_id = rng.choice(profile["devices"])
                summary = f"Ticket for {device_id} setup"
                status = rng.choice(["open", "closed", "resolved"])
            elif record_type == "travel_notice":
                device_id = None
                summary = f"{user_id} traveling to UTC+{rng.randint(-12, 12)}"
                status = "active"
            else:  # hr_note
                device_id = None
                summary = f"HR note for {user_id}: role change"
                status = "archived"

            ts = datetime(2024, 1, rng.randint(1, 30), tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")

            records.append({
                "record_id": f"CTX-{record_id_counter:04d}",
                "ts": ts,
                "user_id": user_id,
                "record_type": record_type,
                "device_id": device_id,
                "summary": summary,
                "status": status,
            })

    return records


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic history database")
    parser.add_argument("--db", default="data/history.db", help="Output database path")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    # Generate data
    events = generate_history(args.seed)
    profiles = {u: generate_user_profile(random.Random(args.seed), u) for u in USERS}
    rng = random.Random(args.seed)
    context_records = generate_context_records(rng, profiles)

    # Write to database
    Path(args.db).parent.mkdir(parents=True, exist_ok=True)
    conn = connect(args.db)
    create_schema(conn)
    insert_events(conn, events)
    insert_context(conn, context_records)

    # Print summary
    print(f"Generated {len(events)} events for {len(USERS)} users")
    print(f"Generated {len(context_records)} context records")
    print(f"Database: {args.db}")

    # Per-user counts
    user_counts = {}
    for e in events:
        user_counts[e["user_id"]] = user_counts.get(e["user_id"], 0) + 1
    for u in USERS:
        print(f"  {u}: {user_counts.get(u, 0)} events")

    conn.close()


if __name__ == "__main__":
    main()