#!/usr/bin/env python
"""
Verify a Phase 3 investigation result.
Loads results/demo.json, rebuilds the scenario DB, runs verification, prints table.
"""
import json
from pathlib import Path

from src.scenario import load_scenario, build_session
from src.investigator import InvestigationResult
from src.evidence_verifier import verify_investigation, print_verification_report


def main():
    results_path = Path("results/demo.json")
    if not results_path.exists():
        print(f"Results file not found: {results_path}")
        print("Run Phase 3 investigation first: python -m src.investigator --scenario data/demo_scenario.json --out results/demo.json --mode json")
        return

    # Load investigation result
    with open(results_path, "r") as f:
        data = json.load(f)
    
    result = InvestigationResult.model_validate(data)
    
    if not result.investigation:
        print(f"Investigation failed or incomplete. Status: {result.status}")
        return
    
    # Load scenario and rebuild session
    scenario = load_scenario("data/demo_scenario.json")
    session = build_session(scenario)
    
    # Verify
    report = verify_investigation(
        result.investigation,
        session.conn,
        scenario["baseline_cutoff"],
        result.retrieved_event_ids,
        result.retrieved_record_ids,
    )
    
    print_verification_report(report)
    
    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    s = report.summary
    print(f"Total claims: {s['total_claims']}")
    print(f"VERIFIED: {s['status_counts'].get('VERIFIED', 0)}")
    print(f"FAILED: {s['status_counts'].get('FAILED', 0)}")
    print(f"NOT_CHECKABLE: {s['status_counts'].get('NOT_CHECKABLE', 0)}")
    print(f"Valid citation rate: {s['valid_citation_rate']:.1%}")
    print(f"Unsupported claim rate: {s['unsupported_claim_rate']:.1%}")
    
    session.conn.close()


if __name__ == "__main__":
    main()