#!/usr/bin/env python
"""
Demo script showing each tool working on the history database.
"""
from src.event_tools import create_session, dispatch, TOOL_SCHEMAS


def main():
    db_path = "data/history.db"
    baseline_cutoff = "2024-01-21T00:00:00Z"  # Days 1-20 as baseline

    print("=" * 60)
    print("CyberImmune Tool Demo")
    print(f"Database: {db_path}")
    print(f"Baseline cutoff: {baseline_cutoff}")
    print("=" * 60)

    session = create_session(db_path, baseline_cutoff)

    # Tool 1: query_events
    print("\n--- query_events ---")
    print("Call: query_events(user_id='user_01', event_type='login', limit=3)")
    result = dispatch(session, "query_events", {
        "user_id": "user_01",
        "event_type": "login",
        "limit": 3
    })
    print(f"OK: {result['ok']}")
    print(f"Rows: {result.get('row_count', 0)}")
    if result['ok']:
        for row in result['data']:
            print(f"  {row['event_id']} | {row['ts']} | {row['event_type']} | {row['device_id']} | {row.get('details_untrusted', '')[:50]}")

    # Tool 2: get_baseline
    print("\n--- get_baseline ---")
    print("Call: get_baseline(user_id='user_01')")
    result = dispatch(session, "get_baseline", {"user_id": "user_01"})
    print(f"OK: {result['ok']}")
    if result['ok']:
        data = result['data']
        print(f"  Baseline logins: {data['baseline_login_count']}")
        print(f"  Baseline sufficient: {data['baseline_sufficient']}")
        print(f"  Known devices: {len(data['known_devices'])}")
        print(f"  Top resources: {data['top_resources'][:3]}")
        print(f"  Avg events/day: {data['avg_events_per_day']}")

    # Tool 3: get_context
    print("\n--- get_context ---")
    print("Call: get_context(user_id='user_01', limit=3)")
    result = dispatch(session, "get_context", {"user_id": "user_01", "limit": 3})
    print(f"OK: {result['ok']}")
    print(f"Rows: {result.get('row_count', 0)}")
    if result['ok']:
        for row in result['data']:
            print(f"  {row['record_id']} | {row['ts']} | {row['record_type']} | {row.get('summary_untrusted', '')[:50]}")

    # Show audit log
    print("\n--- Audit Log ---")
    for entry in session.audit_log:
        status = "OK" if entry['ok'] else "ERROR"
        print(f"  {entry['tool']}({entry['args']}) -> {status} ({entry['row_count']} rows)")

    # Show tool schemas (for model)
    print("\n--- Tool Schemas (for model) ---")
    import json
    for schema in TOOL_SCHEMAS:
        print(json.dumps(schema, indent=2))

    session.conn.close()


if __name__ == "__main__":
    main()