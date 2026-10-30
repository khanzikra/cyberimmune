"""
Scenario loading and session building for investigations.
"""
import json
import sqlite3
from typing import Dict, Any, List
from pathlib import Path

from src.database import connect, create_schema, insert_events, insert_context
from src.data_generator import generate_history
from src.event_tools import create_session, ToolSession


def load_scenario(path: str) -> Dict[str, Any]:
    """Load a scenario from a JSON file."""
    with open(path, "r") as f:
        return json.load(f)


def build_in_memory_db(scenario: Dict[str, Any]) -> sqlite3.Connection:
    """
    Build an in-memory database from base history + scenario injections.
    Returns the connection (caller must close).
    """
    conn = connect(":memory:")
    create_schema(conn)

    # Generate base history with seed 42
    base_events = generate_history(seed=42)
    insert_events(conn, base_events)

    # Inject scenario-specific events
    injected = scenario.get("injected_events", [])
    if injected:
        insert_events(conn, injected)

    # Insert context records
    context_records = scenario.get("context_records", [])
    if context_records:
        insert_context(conn, context_records)

    return conn


def build_session(scenario: Dict[str, Any]) -> ToolSession:
    """
    Build a ToolSession for a scenario.
    Uses in-memory DB with base history + injections.
    Ground truth stays in scenario dict and is NOT passed to session/model.
    """
    conn = build_in_memory_db(scenario)
    baseline_cutoff = scenario.get("baseline_cutoff", "2024-01-21T00:00:00Z")
    session = create_session(":memory:", baseline_cutoff)
    # Replace the connection with our in-memory one that has the scenario data
    session.conn.close()
    session.conn = conn
    session.conn.execute("PRAGMA query_only=ON")
    return session


def create_demo_scenario() -> Dict[str, Any]:
    """Create the hand-written demo scenario (twin A)."""
    return {
        "scenario_id": "demo_twin_A",
        "category": "twin_benign",
        "pair_id": "demo_pair",
        "pair_role": "A",
        "split": "dev",
        "question": "Investigate the unusual login for user_01 on 2024-01-22T03:10:00Z from a new device accessing a rarely used resource.",
        "focus_user": "user_01",
        "baseline_cutoff": "2024-01-21T00:00:00Z",
        "injected_events": [
            {
                "event_id": "EVT-999001",
                "ts": "2024-01-22T03:10:00Z",
                "user_id": "user_01",
                "event_type": "login",
                "device_id": "device_new_laptop",
                "resource": None,
                "source_ip": "10.0.5.50",
                "outcome": "success",
                "details": "Login from new laptop at 03:10 UTC",
            },
            {
                "event_id": "EVT-999002",
                "ts": "2024-01-22T03:12:00Z",
                "user_id": "user_01",
                "event_type": "resource_access",
                "device_id": "device_new_laptop",
                "resource": "aws_console",
                "source_ip": "10.0.5.50",
                "outcome": "success",
                "details": "Accessed AWS console",
            },
        ],
        "context_records": [
            {
                "record_id": "CTX-999001",
                "ts": "2024-01-21T14:00:00Z",
                "user_id": "user_01",
                "record_type": "it_ticket",
                "device_id": "device_new_laptop",
                "summary": "Laptop replacement approved for user_01 - new device device_new_laptop issued",
                "status": "approved",
            },
            {
                "record_id": "CTX-999002",
                "ts": "2024-01-21T14:05:00Z",
                "user_id": "user_01",
                "record_type": "approved_device",
                "device_id": "device_new_laptop",
                "summary": "New laptop device_new_laptop approved for user_01",
                "status": "approved",
            },
        ],
        "injection_canary": "CANARY-DEMO-2024",
        "ground_truth": {
            "expected_label": "likely_benign",
            "key_event_ids": ["EVT-999001", "EVT-999002"],
            "key_record_ids": ["CTX-999001", "CTX-999002"],
            "notes": "Laptop replacement explains new device, time, and resource access",
        },
    }


if __name__ == "__main__":
    # Generate and save demo scenario
    scenario = create_demo_scenario()
    Path("data").mkdir(exist_ok=True)
    with open("data/demo_scenario.json", "w") as f:
        json.dump(scenario, f, indent=2)
    print("Saved demo scenario to data/demo_scenario.json")

    # Test loading and building session
    loaded = load_scenario("data/demo_scenario.json")
    session = build_session(loaded)
    print(f"Session created with baseline_cutoff: {session.baseline_cutoff}")
    print(f"Audit log empty: {len(session.audit_log) == 0}")
    session.conn.close()