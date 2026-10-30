"""
Flag rate analysis script.
Uses days 1-20 as baseline, reports share of normal events on days 21-30 flagged per rule.
"""
import sqlite3
from src.database import connect
from src.baseline import compute_baseline, find_indicators


def main():
    db_path = "data/history.db"
    conn = connect(db_path)

    # Use days 1-20 as baseline (cutoff at day 21 start)
    cutoff = "2024-01-21T00:00:00Z"
    window_start = "2024-01-21T00:00:00Z"
    window_end = "2024-01-30T23:59:59Z"

    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT user_id FROM events ORDER BY user_id")
    users = [row["user_id"] for row in cursor.fetchall()]

    total_events = 0
    rule_counts = {
        "R1_unusual_hour": 0,
        "R2_new_device": 0,
        "R3_rare_resource": 0,
        "R4_failure_burst": 0,
    }

    print("Flag Rate Analysis (Baseline: Days 1-20, Test: Days 21-30)")
    print("=" * 60)

    for user_id in users:
        baseline = compute_baseline(conn, user_id, cutoff)
        print(f"\n{user_id}:")
        print(f"  Baseline logins: {baseline['baseline_login_count']}, sufficient: {baseline['baseline_sufficient']}")

        indicators = find_indicators(conn, user_id, cutoff, window_start, window_end)

        # Count events in window
        cursor.execute("""
            SELECT COUNT(*) FROM events
            WHERE user_id = ? AND ts >= ? AND ts <= ?
        """, (user_id, window_start, window_end))
        user_event_count = cursor.fetchone()[0]
        total_events += user_event_count

        # Count by rule
        user_rule_counts = {k: 0 for k in rule_counts}
        for ind in indicators:
            if ind["rule"] in user_rule_counts:
                user_rule_counts[ind["rule"]] += 1
                rule_counts[ind["rule"]] += 1

        print(f"  Events in window: {user_event_count}")
        for rule, count in user_rule_counts.items():
            rate = count / user_event_count if user_event_count > 0 else 0
            print(f"  {rule}: {count} ({rate:.1%})")

    print("\n" + "=" * 60)
    print("OVERALL FLAG RATES:")
    print(f"Total events in test window: {total_events}")
    for rule, count in rule_counts.items():
        rate = count / total_events if total_events > 0 else 0
        print(f"  {rule}: {count} ({rate:.1%})")

    conn.close()


if __name__ == "__main__":
    main()