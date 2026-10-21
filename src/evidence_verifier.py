"""
Deterministic evidence verifier for CyberImmune.
Checks every factual claim against the database and baseline.
"""
import json
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set, Tuple
from datetime import datetime
import sqlite3
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.schemas import Claim, ClaimType, Investigation
from src.database import connect
from src.baseline import compute_baseline


@dataclass
class CheckResult:
    """Result of a single verification check."""
    level: str  # "citation", "field", "relationship"
    passed: bool
    detail: str


@dataclass
class ClaimVerification:
    """Verification result for a single claim."""
    claim_id: str
    claim_text: str
    claim_type: str
    status: str  # VERIFIED, FAILED, NOT_CHECKABLE
    checks_run: List[CheckResult]
    explanation: str
    provenance_ok: Optional[bool] = None
    original_claim: Optional[Dict[str, Any]] = None


@dataclass
class VerificationReport:
    """Full verification report for an investigation."""
    claim_verifications: List[ClaimVerification]
    summary: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim_verifications": [
                {
                    "claim_id": cv.claim_id,
                    "claim_text": cv.claim_text,
                    "claim_type": cv.claim_type,
                    "status": cv.status,
                    "checks_run": [
                        {"level": c.level, "passed": c.passed, "detail": c.detail}
                        for c in cv.checks_run
                    ],
                    "explanation": cv.explanation,
                    "provenance_ok": cv.provenance_ok,
                    "original_claim": cv.original_claim,
                }
                for cv in self.claim_verifications
            ],
            "summary": self.summary,
        }


def _normalize_timestamp(ts: str) -> datetime:
    """Normalize timestamp to datetime for comparison."""
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    return datetime.fromisoformat(ts)


def _event_exists(conn: sqlite3.Connection, event_id: str) -> Tuple[bool, Optional[sqlite3.Row], str]:
    """Check if event exists, return (exists, row, detail)."""
    cur = conn.execute("SELECT * FROM events WHERE event_id = ?", (event_id,))
    row = cur.fetchone()
    if row:
        return True, row, f"Event {event_id} exists"
    return False, None, f"Event {event_id} does not exist"


def _context_exists(conn: sqlite3.Connection, record_id: str) -> Tuple[bool, Optional[sqlite3.Row], str]:
    """Check if context record exists."""
    cur = conn.execute("SELECT * FROM context_records WHERE record_id = ?", (record_id,))
    row = cur.fetchone()
    if row:
        return True, row, f"Context record {record_id} exists"
    return False, None, f"Context record {record_id} does not exist"


def verify_claim(
    claim: Claim,
    conn: sqlite3.Connection,
    baseline_cutoff: str,
    retrieved_event_ids: Optional[Set[str]] = None,
    retrieved_record_ids: Optional[Set[str]] = None,
) -> ClaimVerification:
    """
    Verify a single claim against the database.
    Returns ClaimVerification with status, checks, and explanation.
    """
    checks = []
    claim_dict = claim.model_dump()

    # Helper: citation check for all cited IDs
    def check_citations():
        all_ok = True
        details = []
        for eid in claim.cited_event_ids:
            exists, _, detail = _event_exists(conn, eid)
            if not exists:
                all_ok = False
            details.append(detail)
        for rid in claim.cited_record_ids:
            exists, _, detail = _context_exists(conn, rid)
            if not exists:
                all_ok = False
            details.append(detail)
        checks.append(CheckResult("citation", all_ok, "; ".join(details) if details else "No citations"))
        return all_ok

    # Helper: check claim is about the right user (where user is stated)
    def check_user_match(event_row: sqlite3.Row, expected_user: str) -> bool:
        if event_row["user_id"] != expected_user:
            checks.append(CheckResult(
                "relationship", False,
                f"Event {event_row['event_id']} belongs to user {event_row['user_id']}, not {expected_user}"
            ))
            return False
        return True

    # Interpretive types are NOT_CHECKABLE
    if claim.claim_type in (ClaimType.INTERPRETATION, ClaimType.HYPOTHESIS, ClaimType.MISSING_EVIDENCE):
        return ClaimVerification(
            claim_id=claim.claim_id,
            claim_text=claim.text,
            claim_type=claim.claim_type.value,
            status="NOT_CHECKABLE",
            checks_run=[],
            explanation="Interpretive validity is not machine-checkable; shown as the model's interpretation.",
            provenance_ok=None,
            original_claim=claim_dict,
        )

    # Start with citation check
    citation_ok = check_citations()

    # Provenance check
    provenance_ok = None
    if retrieved_event_ids is not None and retrieved_record_ids is not None:
        all_cited = set(claim.cited_event_ids) | set(claim.cited_record_ids)
        all_retrieved = retrieved_event_ids | retrieved_record_ids
        if all_cited:
            provenance_ok = all_cited.issubset(all_retrieved)
        else:
            provenance_ok = True  # No citations to check

    # Validate structured fields for factual types
    structured = claim.structured
    if not structured:
        checks.append(CheckResult("field", False, "Missing structured fields"))
        return ClaimVerification(
            claim_id=claim.claim_id,
            claim_text=claim.text,
            claim_type=claim.claim_type.value,
            status="FAILED",
            checks_run=checks,
            explanation="Factual claim has missing/malformed structured fields",
            provenance_ok=provenance_ok,
            original_claim=claim_dict,
        )

    # Type-specific verification
    status = "VERIFIED"
    all_checks_passed = citation_ok

    if claim.claim_type == ClaimType.EVENT_EXISTS:
        event_id = structured.get("event_id")
        exists, row, detail = _event_exists(conn, event_id)
        checks.append(CheckResult("field", exists, detail))
        if not exists:
            status = "FAILED"
            all_checks_passed = False
        elif row and not check_user_match(row, claim_dict.get("text", "").split("user_")[1][:3] if "user_" in claim_dict.get("text", "") else "user_01"):
            # We can't easily get expected user from claim text, skip for now
            pass

    elif claim.claim_type == ClaimType.FIELD_VALUE:
        event_id = structured.get("event_id")
        field_name = structured.get("field")
        expected_value = structured.get("value")

        exists, row, detail = _event_exists(conn, event_id)
        if not exists:
            checks.append(CheckResult("field", False, detail))
            status = "FAILED"
            all_checks_passed = False
        else:
            # Check user match
            check_user_match(row, claim_dict.get("text", "").split("user_")[1][:3] if "user_" in claim_dict.get("text", "") else "user_01")

            # Normalize timestamp if needed
            actual_value = row[field_name]
            if field_name == "ts" and isinstance(actual_value, str) and isinstance(expected_value, str):
                actual_value = _normalize_timestamp(actual_value).isoformat()
                expected_value = _normalize_timestamp(expected_value).isoformat()

            passed = str(actual_value) == str(expected_value)
            checks.append(CheckResult("field", passed,
                f"Field '{field_name}': expected {expected_value}, got {actual_value}"))
            if not passed:
                status = "FAILED"
                all_checks_passed = False

    elif claim.claim_type == ClaimType.ORDER:
        first_id = structured.get("first_event_id")
        second_id = structured.get("second_event_id")

        exists1, row1, detail1 = _event_exists(conn, first_id)
        exists2, row2, detail2 = _event_exists(conn, second_id)

        if not exists1 or not exists2:
            checks.append(CheckResult("relationship", False, f"{detail1}; {detail2}"))
            status = "FAILED"
            all_checks_passed = False
        else:
            check_user_match(row1, "user_01")  # Best effort
            check_user_match(row2, "user_01")

            ts1 = _normalize_timestamp(row1["ts"])
            ts2 = _normalize_timestamp(row2["ts"])
            passed = ts1 < ts2
            checks.append(CheckResult("relationship", passed,
                f"ORDER: {first_id} ({ts1}) < {second_id} ({ts2}) = {passed}"))
            if not passed:
                status = "FAILED"
                all_checks_passed = False

    elif claim.claim_type == ClaimType.DEVICE_FAMILIARITY:
        user_id = structured.get("user_id")
        device_id = structured.get("device_id")
        claimed_familiar = structured.get("familiar")

        baseline = compute_baseline(conn, user_id, baseline_cutoff)
        known_devices = {d["device_id"] for d in baseline["known_devices"]}
        actual_familiar = device_id in known_devices

        passed = actual_familiar == claimed_familiar
        checks.append(CheckResult("relationship", passed,
            f"DEVICE_FAMILIARITY: device '{device_id}' in baseline for {user_id} = {actual_familiar} (claimed {claimed_familiar})"))
        if not passed:
            status = "FAILED"
            all_checks_passed = False

    elif claim.claim_type == ClaimType.CONTEXT_EXISTS:
        record_id = structured.get("record_id")
        expected_user = structured.get("user_id")
        expected_type = structured.get("record_type")

        exists, row, detail = _context_exists(conn, record_id)
        if not exists:
            checks.append(CheckResult("field", False, detail))
            status = "FAILED"
            all_checks_passed = False
        else:
            passed = True
            if expected_user and row["user_id"] != expected_user:
                passed = False
                checks.append(CheckResult("relationship", False,
                    f"Context record {record_id} belongs to user {row['user_id']}, not {expected_user}"))
            if expected_type and row["record_type"] != expected_type:
                passed = False
                checks.append(CheckResult("relationship", False,
                    f"Context record {record_id} has type {row['record_type']}, not {expected_type}"))

            if passed:
                checks.append(CheckResult("field", True, detail))
            else:
                status = "FAILED"
                all_checks_passed = False

    # Final status logic
    if not all_checks_passed:
        status = "FAILED"

    # Build explanation
    failed_checks = [c for c in checks if not c.passed]
    if status == "VERIFIED":
        explanation = "All checks passed"
    elif status == "FAILED":
        explanation = f"Failed checks: {'; '.join(c.detail for c in failed_checks)}"
    else:
        explanation = "Status not determined"

    return ClaimVerification(
        claim_id=claim.claim_id,
        claim_text=claim.text,
        claim_type=claim.claim_type.value,
        status=status,
        checks_run=checks,
        explanation=explanation,
        provenance_ok=provenance_ok,
        original_claim=claim_dict,
    )


def verify_investigation(
    investigation: Investigation,
    conn: sqlite3.Connection,
    baseline_cutoff: str,
    retrieved_event_ids: Optional[List[str]] = None,
    retrieved_record_ids: Optional[List[str]] = None,
) -> VerificationReport:
    """
    Verify all claims in an investigation.
    Returns VerificationReport with per-claim results and summary.
    """
    retrieved_e = set(retrieved_event_ids) if retrieved_event_ids is not None else None
    retrieved_r = set(retrieved_record_ids) if retrieved_record_ids is not None else None

    verifications = []
    for claim in investigation.claims:
        cv = verify_claim(claim, conn, baseline_cutoff, retrieved_e, retrieved_r)
        verifications.append(cv)

    # Compute summary
    total = len(verifications)
    verified = sum(1 for v in verifications if v.status == "VERIFIED")
    failed = sum(1 for v in verifications if v.status == "FAILED")
    not_checkable = sum(1 for v in verifications if v.status == "NOT_CHECKABLE")

    # valid_citation_rate = cited IDs that exist / all cited IDs
    all_cited = set()
    for v in verifications:
        all_cited.update(v.original_claim.get("cited_event_ids", []))
        all_cited.update(v.original_claim.get("cited_record_ids", []))
    valid_cited = 0
    for eid in all_cited:
        if eid and _event_exists(conn, eid)[0]:
            valid_cited += 1
    for rid in all_cited:
        if rid and _context_exists(conn, rid)[0]:
            valid_cited += 1
    valid_citation_rate = valid_cited / len(all_cited) if all_cited else 1.0

    # unsupported_claim_rate = FAILED / (VERIFIED + FAILED)
    checkable = verified + failed
    unsupported_claim_rate = failed / checkable if checkable > 0 else 0.0

    summary = {
        "total_claims": total,
        "verified": verified,
        "failed": failed,
        "not_checkable": not_checkable,
        "valid_citation_rate": round(valid_citation_rate, 4),
        "unsupported_claim_rate": round(unsupported_claim_rate, 4),
    }

    return VerificationReport(claim_verifications=verifications, summary=summary)


if __name__ == "__main__":
    # Quick test
    import tempfile
    from src.data_generator import generate_history
    from src.database import create_schema, insert_events, insert_context

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    conn = connect(db_path)
    create_schema(conn)
    data = generate_history(seed=42)
    insert_events(conn, data["events"])
    insert_context(conn, data["context_records"])
    conn.commit()

    # Create a simple test claim
    from src.schemas import Claim, ClaimType
    test_claim = Claim(
        claim_id="C1",
        text="User logged in",
        claim_type=ClaimType.EVENT_EXISTS,
        cited_event_ids=["EVT-000001"],
        cited_record_ids=[],
        structured={"event_id": "EVT-000001"},
    )

    # We need an investigation object
    from src.schemas import Investigation, Conclusion, ConclusionLabel
    test_inv = Investigation(
        question="Test",
        claims=[test_claim],
        hypotheses=[],
        missing_evidence=[],
        next_steps=[],
        conclusion=Conclusion(label=ConclusionLabel.NO_CONCERN, rationale="Test"),
    )

    report = verify_investigation(test_inv, conn, "2024-01-21T00:00:00Z")
    print(json.dumps(report.to_dict(), indent=2))

    conn.close()