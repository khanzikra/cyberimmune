"""
Script: loads a results JSON from Phase 3 + rebuilds its scenario DB,
prints a readable table of claim, status, reason.
"""
import json
import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.investigator import run_investigation
from src.scenario import load_scenario, build_session
from src.schemas import Investigation
from src.evidence_verifier import verify_investigation


def main():
    parser = argparse.ArgumentParser(description="Verify investigation result against scenario DB")
    parser.add_argument("--result", required=True, help="Path to results JSON from Phase 3")
    parser.add_argument("--scenario", required=True, help="Path to scenario JSON")
    args = parser.parse_args()

    # Load result
    with open(args.result, "r") as f:
        result_data = json.load(f)

    if not result_data.get("investigation"):
        print("No investigation in result (status: {})".format(result_data.get("status")))
        return

    investigation = Investigation(**result_data["investigation"])

    # Load scenario and build session (rebuilds DB)
    scenario = load_scenario(args.scenario)
    session = build_session(scenario)

    # Get retrieved IDs from result
    retrieved_events = result_data.get("retrieved_event_ids", [])
    retrieved_records = result_data.get("retrieved_record_ids", [])

    # Verify
    report = verify_investigation(
        investigation,
        session.conn,
        scenario["baseline_cutoff"],
        retrieved_event_ids=retrieved_events,
        retrieved_record_ids=retrieved_records,
    )

    # Print readable table
    print(f"\n{'='*100}")
    print(f"VERIFICATION REPORT")
    print(f"{'='*100}")
    print(f"Result file: {args.result}")
    print(f"Scenario: {args.scenario}")
    print(f"Focus user: {scenario.get('focus_user', 'N/A')}")
    print(f"Baseline cutoff: {scenario['baseline_cutoff']}")
    print(f"{'='*100}\n")

    print(f"{'Claim':<5} {'Type':<22} {'Status':<12} {'Reason'}")
    print(f"{'-'*5} {'-'*22} {'-'*12} {'-'*50}")

    for cv in report.claim_verifications:
        status = cv.status
        reason = cv.explanation
        if cv.provenance_ok is False:
            reason += " [PROVENANCE WARNING: cited ID not in retrieved set]"
        elif cv.provenance_ok is True:
            reason += " [provenance OK]"

        # Truncate reason for display
        if len(reason) > 60:
            reason = reason[:57] + "..."

        print(f"{cv.claim_id:<5} {cv.claim_type:<22} {status:<12} {reason}")

    # Print summary
    print(f"\n{'='*100}")
    print(f"SUMMARY")
    print(f"{'='*100}")
    s = report.summary
    print(f"  Total claims:      {s['total_claims']}")
    print(f"  Verified:          {s['verified']}")
    print(f"  Failed:            {s['failed']}")
    print(f"  Not checkable:     {s['not_checkable']}")
    print(f"  Valid citation rate:   {s['valid_citation_rate']:.1%}")
    print(f"  Unsupported claim rate: {s['unsupported_claim_rate']:.1%}")

    # Show failed claims in detail
    failed = [cv for cv in report.claim_verifications if cv.status == "FAILED"]
    if failed:
        print(f"\n{'='*100}")
        print(f"FAILED CLAIMS DETAIL")
        print(f"{'='*100}")
        for cv in failed:
            print(f"\n{cv.claim_id}: {cv.claim_text}")
            print(f"  Type: {cv.claim_type}")
            for check in cv.checks_run:
                mark = "✓" if check.passed else "✗"
                print(f"  {mark} [{check.level}] {check.detail}")


if __name__ == "__main__":
    main()