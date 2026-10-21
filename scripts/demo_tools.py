"""
Demo script: builds a session on data/history.db and prints one call of each tool.
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.event_tools import ToolSession, dispatch


def main():
    db_path = "data/history.db"
    baseline_cutoff = "2024-01-21T00:00:00Z"

    print(f"Creating session on {db_path} with cutoff {baseline_cutoff}")
    session = ToolSession.create(db_path, baseline_cutoff)

    print("\n" + "=" * 60)
    print("TOOL 1: query_events")
    print("=" * 60)
    result = dispatch(session, "query_events", {
        "user_id": "user_01",
        "event_type": "login",
        "limit": 3
    })
    print(f"ok: {result['ok']}")
    if result["ok"]:
        for event in result["data"]:
            print(f"  {event['event_id']} | {event['ts']} | {event['event_type']} | {event['device_id']} | {event.get('details_untrusted', '')[:50]}")
    else:
        print(f"  Error: {result['error']}")

    print("\n" + "=" * 60)
    print("TOOL 2: get_baseline")
    print("=" * 60)
    result = dispatch(session, "get_baseline", {
        "user_id": "user_01"
    })
    print(f"ok: {result['ok']}")
    if result["ok"]:
        data = result["data"]
        print(f"  baseline_login_count: {data['baseline_login_count']}")
        print(f"  baseline_sufficient: {data['baseline_sufficient']}")
        print(f"  known_devices: {len(data['known_devices'])}")
        print(f"  top_resources: {data['top_resources'][:3]}")
        print(f"  avg_events_per_day: {data['avg_events_per_day']}")
        print(f"  cutoff: {data['cutoff']}")
    else:
        print(f"  Error: {result['error']}")

    print("\n" + "=" * 60)
    print("TOOL 3: get_context")
    print("=" * 60)
    result = dispatch(session, "get_context", {
        "user_id": "user_01",
        "limit": 3
    })
    print(f"ok: {result['ok']}")
    if result["ok"]:
        for record in result["data"]:
            print(f"  {record['record_id']} | {record['ts']} | {record['record_type']} | {record.get('summary_untrusted', '')[:50]}")
    else:
        print(f"  Error: {result['error']}")

    print("\n" + "=" * 60)
    print("AUDIT LOG")
    print("=" * 60)
    for entry in session.audit_log:
        status = "OK" if entry["ok"] else "ERROR"
        print(f"  [{status}] {entry['tool']} | args={entry['args']} | rows={entry['row_count']} | error={entry['error']}")


if __name__ == "__main__":
    main()