"""
Flag rate analysis: uses days 1-20 as baseline, reports share of normal
events on days 21-30 that the rules flag, per rule.
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import connect
from src.baseline import compute_baseline, find_indicators
from src.data_generator import write_db


def analyze_flag_rates(db_path: str = "data/history.db") -> None:
    """Analyze and print flag rates per rule."""
    conn = connect(db_path)

    cutoff = "2024-01-21T00:00:00Z"
    window_start = "2024-01-21T00:00:00Z"
    window_end = "2024-01-31T23:59:59Z"

    users = [f"user_{i:02d}" for i in range(1, 11)]

    total_events = 0
    rule_counts = {"R1": 0, "R2": 0, "R3": 0, "R4": 0}
    rule_events = {"R1": set(), "R2": set(), "R3": set(), "R4": set()}

    for user_id in users:
        baseline = compute_baseline(conn, user_id, cutoff)
        print(f"\n{user_id}: baseline_logins={baseline['baseline_login_count']}, "
              f"sufficient={baseline['baseline_sufficient']}")

        indicators = find_indicators(conn, user_id, cutoff, window_start, window_end)

        # Count focus window events
        cur = conn.execute("""
            SELECT COUNT(*) as cnt FROM events
            WHERE user_id = ? AND ts >= ? AND ts <= ?
        """, (user_id, window_start, window_end))
        focus_count = cur.fetchone()["cnt"]
        total_events += focus_count

        for ind in indicators:
            rule = ind["rule"]
            rule_counts[rule] += 1
            rule_events[rule].add(ind["event_id"])

        print(f"  Focus events: {focus_count}, Indicators: {len(indicators)}")
        for ind in indicators:
            print(f"    {ind['rule']}: {ind['event_id']} - {ind['detail']}")

    print("\n" + "=" * 60)
    print("FLAG RATE ANALYSIS (Days 21-30, per rule)")
    print("=" * 60)
    print(f"Total focus window events: {total_events}")
    print()

    for rule in ["R1", "R2", "R3", "R4"]:
        unique_flagged = len(rule_events[rule])
        rate = unique_flagged / total_events * 100 if total_events > 0 else 0
        print(f"{rule}: {unique_flagged} unique events flagged ({rate:.1f}% of focus events)")

    print("\nNote: These are raw flag rates on synthetic data. Do not tune to look good.")


if __name__ == "__main__":
    # Generate DB if not exists
    db_path = Path("data/history.db")
    if not db_path.exists():
        print("Generating database...")
        write_db(str(db_path), seed=42)

    analyze_flag_rates(str(db_path))