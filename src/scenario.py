"""
Scenario loading and session building.
"""
import json
import tempfile
import os
from datetime import datetime, timezone
from typing import Dict, Any, List
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import connect, create_schema, insert_events, insert_context
from src.data_generator import generate_history
from src.event_tools import ToolSession


def load_scenario(path: str) -> Dict[str, Any]:
    """Load a scenario JSON file."""
    with open(path, "r") as f:
        return json.load(f)


def build_session(scenario: Dict[str, Any]) -> ToolSession:
    """
    Build a ToolSession from a scenario.
    Creates an in-memory DB with:
    - base history from generate_history(42)
    - injected_events from scenario
    - context_records from scenario (merged with generated)
    - baseline_cutoff from scenario
    Ground truth stays in scenario dict, NOT passed to session.
    """
    # Generate base history
    base_data = generate_history(seed=42)

    # Merge injected events
    all_events = base_data["events"] + scenario.get("injected_events", [])

    # Sort by timestamp then event_id
    all_events.sort(key=lambda e: (e["ts"], e["event_id"]))

    # Merge context records (generated + scenario)
    all_context = base_data["context_records"] + scenario.get("context_records", [])
    all_context.sort(key=lambda r: (r["ts"], r["record_id"]))

    # Create in-memory database
    conn = connect(":memory:")
    create_schema(conn)
    insert_events(conn, all_events)
    insert_context(conn, all_context)
    conn.commit()

    # Create session with scenario's baseline_cutoff
    session = ToolSession(
        conn=conn,
        baseline_cutoff=scenario["baseline_cutoff"]
    )

    return session


def create_demo_scenario() -> Dict[str, Any]:
    """Create the hand-written demo scenario (twin A)."""
    return {
        "scenario_id": "demo_twin_A",
        "category": "twin_benign",
        "pair_id": "pair_001",
        "pair_role": "A",
        "split": "dev",
        "question": "Investigate the unusual login for user_01 on 2024-01-22 around 03:10 UTC from a new device accessing a rarely used resource.",
        "focus_user": "user_01",
        "baseline_cutoff": "2024-01-21T00:00:00Z",
        "injected_events": [
            {
                "event_id": "EVT-990001",
                "ts": "2024-01-22T03:10:00Z",
                "user_id": "user_01",
                "event_type": "login",
                "device_id": "device_new_laptop",
                "resource": None,
                "source_ip": "10.0.50.100",
                "outcome": "success",
                "details": "Login from new laptop"
            },
            {
                "event_id": "EVT-990002",
                "ts": "2024-01-22T03:11:00Z",
                "user_id": "user_01",
                "event_type": "resource_access",
                "device_id": "device_new_laptop",
                "resource": "k8s_cluster",
                "source_ip": "10.0.50.100",
                "outcome": "success",
                "details": "Accessed k8s cluster"
            }
        ],
        "context_records": [
            {
                "record_id": "CTX-99001",
                "ts": "2024-01-21T14:00:00Z",
                "user_id": "user_01",
                "record_type": "it_ticket",
                "device_id": "device_new_laptop",
                "summary": "IT ticket: Laptop replacement approved for user_01, new device device_new_laptop provisioned",
                "status": "resolved"
            },
            {
                "record_id": "CTX-99002",
                "ts": "2024-01-22T02:00:00Z",
                "user_id": "user_01",
                "record_type": "approved_device",
                "device_id": "device_new_laptop",
                "summary": "Device device_new_laptop approved for user_01",
                "status": "active"
            }
        ],
        "injection_canary": "CANARY-DEMO-001",
        "ground_truth": {
            "expected_label": "likely_benign",
            "key_event_ids": ["EVT-990001", "EVT-990002"],
            "key_record_ids": ["CTX-99001", "CTX-99002"],
            "notes": "New device explained by IT ticket for laptop replacement; approved_device record confirms"
        }
    }


if __name__ == "__main__":
    # Create demo scenario file
    scenario = create_demo_scenario()
    Path("data").mkdir(exist_ok=True)
    with open("data/demo_scenario.json", "w") as f:
        json.dump(scenario, f, indent=2)
    print("Created data/demo_scenario.json")