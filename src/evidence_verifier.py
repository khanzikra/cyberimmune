"""
Deterministic evidence verifier for CyberImmune.
Checks every checkable claim against the database and baseline.
"""
import json
from datetime import datetime
from typing import Dict, List, Any, Optional, Literal, Set
from dataclasses import dataclass, field
from enum import Enum

from src.database import connect
from src.baseline import compute_baseline
from src.schemas import Claim, ClaimType, Investigation


class CheckLevel(str, Enum):
    CITATION = "citation"
    FIELD = "field"
    RELATIONSHIP = "relationship"


class VerificationStatus(str, Enum):
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    NOT_CHECKABLE = "NOT_CHECKABLE"


@dataclass
class CheckResult:
    level: CheckLevel
    passed: bool
    detail: str


@dataclass
class ClaimVerification:
    claim_id: str
    claim_text: str
    claim_type: ClaimType
    status: VerificationStatus
    checks_run: List[CheckResult] = field(default_factory=list)
    explanation: str = ""
    provenance_ok: Optional[bool] = None  # True, False, or None if provenance sets not provided


@dataclass
class VerificationReport:
    claim_verifications: List[ClaimVerification]
    summary: Dict[str, Any] = field(default_factory=dict)


def normalize_timestamp(ts: str) -> str:
    """Normalize timestamp to ISO format with Z suffix."""
    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return dt.isoformat().replace("+00:00", "Z")


def verify_citation_event(event_id: str, conn) -> CheckResult:
    """Check if event_id exists in database."""
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM events WHERE event_id = ?", (event_id,))
    exists = cursor.fetchone() is not None
    return CheckResult(
        level=CheckLevel.CITATION,
        passed=exists,
        detail=f"Event {event_id} {'exists' if exists else 'NOT FOUND'}"
    )


def verify_citation_record(record_id: str, conn) -> CheckResult:
    """Check if record_id exists in database."""
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM context_records WHERE record_id = ?", (record_id,))
    exists = cursor.fetchone() is not None
    return CheckResult(
        level=CheckLevel.CITATION,
        passed=exists,
        detail=f"Record {record_id} {'exists' if exists else 'NOT FOUND'}"
    )


def verify_event_user_match(event_id: str, claimed_user_id: str, conn) -> CheckResult:
    """Check if event belongs to the claimed user."""
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM events WHERE event_id = ?", (event_id,))
    row = cursor.fetchone()
    if not row:
        return CheckResult(
            level=CheckLevel.CITATION,
            passed=False,
            detail=f"Event {event_id} not found"
        )
    actual_user = row["user_id"]
    passed = actual_user == claimed_user_id
    return CheckResult(
        level=CheckLevel.FIELD,
        passed=passed,
        detail=f"Event user_id is {actual_user}, claimed {claimed_user_id}"
    )


def verify_record_user_match(record_id: str, claimed_user_id: str, conn) -> CheckResult:
    """Check if context record belongs to the claimed user."""
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM context_records WHERE record_id = ?", (record_id,))
    row = cursor.fetchone()
    if not row:
        return CheckResult(
            level=CheckLevel.CITATION,
            passed=False,
            detail=f"Record {record_id} not found"
        )
    actual_user = row["user_id"]
    passed = actual_user == claimed_user_id
    return CheckResult(
        level=CheckLevel.FIELD,
        passed=passed,
        detail=f"Record user_id is {actual_user}, claimed {claimed_user_id}"
    )


def verify_event_exists(claim: Claim, conn) -> List[CheckResult]:
    """Verify EVENT_EXISTS claim."""
    checks = []
    for eid in claim.cited_event_ids:
        checks.append(verify_citation_event(eid, conn))
    return checks


def verify_field_value(claim: Claim, conn) -> List[CheckResult]:
    """Verify FIELD_VALUE claim: event exists AND field equals value."""
    checks = []
    structured = claim.structured
    
    if not structured or "event_id" not in structured or "field" not in structured or "value" not in structured:
        checks.append(CheckResult(
            level=CheckLevel.FIELD,
            passed=False,
            detail="Malformed structured field: missing event_id, field, or value"
        ))
        return checks
    
    event_id = structured["event_id"]
    field_name = structured["field"]
    expected_value = structured["value"]
    
    # Check citation
    checks.append(verify_citation_event(event_id, conn))
    
    # Get actual value
    cursor = conn.cursor()
    valid_fields = ["user_id", "ts", "event_type", "device_id", "resource", "source_ip", "outcome"]
    if field_name not in valid_fields:
        checks.append(CheckResult(
            level=CheckLevel.FIELD,
            passed=False,
            detail=f"Invalid field name: {field_name}"
        ))
        return checks
    
    cursor.execute(f"SELECT {field_name} FROM events WHERE event_id = ?", (event_id,))
    row = cursor.fetchone()
    
    if not row:
        checks.append(CheckResult(
            level=CheckLevel.FIELD,
            passed=False,
            detail=f"Event {event_id} not found"
        ))
        return checks
    
    actual_value = row[field_name]
    
    # Normalize timestamps for comparison
    if field_name == "ts":
        actual_value = normalize_timestamp(actual_value)
        expected_value = normalize_timestamp(expected_value)
    
    passed = actual_value == expected_value
    checks.append(CheckResult(
        level=CheckLevel.FIELD,
        passed=passed,
        detail=f"Field {field_name}: expected={expected_value}, actual={actual_value}"
    ))
    
    return checks


def verify_order(claim: Claim, conn) -> List[CheckResult]:
    """Verify ORDER claim: both events exist AND first.ts < second.ts."""
    checks = []
    structured = claim.structured
    
    if not structured or "first_event_id" not in structured or "second_event_id" not in structured:
        checks.append(CheckResult(
            level=CheckLevel.RELATIONSHIP,
            passed=False,
            detail="Malformed structured field: missing first_event_id or second_event_id"
        ))
        return checks
    
    first_id = structured["first_event_id"]
    second_id = structured["second_event_id"]
    
    # Check citations
    checks.append(verify_citation_event(first_id, conn))
    checks.append(verify_citation_event(second_id, conn))
    
    cursor = conn.cursor()
    cursor.execute("SELECT event_id, ts FROM events WHERE event_id IN (?, ?)", (first_id, second_id))
    rows = {row["event_id"]: row["ts"] for row in cursor.fetchall()}
    
    if first_id not in rows or second_id not in rows:
        checks.append(CheckResult(
            level=CheckLevel.RELATIONSHIP,
            passed=False,
            detail="One or both events not found"
        ))
        return checks
    
    first_ts = normalize_timestamp(rows[first_id])
    second_ts = normalize_timestamp(rows[second_id])
    
    passed = first_ts < second_ts
    checks.append(CheckResult(
        level=CheckLevel.RELATIONSHIP,
        passed=passed,
        detail=f"First {first_ts} < Second {second_ts}: {passed}"
    ))
    
    return checks


def verify_device_familiarity(claim: Claim, conn, baseline_cutoff: str) -> List[CheckResult]:
    """Verify DEVICE_FAMILIARITY claim: device seen before cutoff == claimed familiar."""
    checks = []
    structured = claim.structured
    
    if not structured or "user_id" not in structured or "device_id" not in structured or "familiar" not in structured:
        checks.append(CheckResult(
            level=CheckLevel.FIELD,
            passed=False,
            detail="Malformed structured field: missing user_id, device_id, or familiar"
        ))
        return checks
    
    user_id = structured["user_id"]
    device_id = structured["device_id"]
    claimed_familiar = structured["familiar"]
    
    # Get baseline known devices
    baseline = compute_baseline(conn, user_id, baseline_cutoff)
    known_devices = {d["device_id"] for d in baseline["known_devices"]}
    actual_familiar = device_id in known_devices
    
    passed = actual_familiar == claimed_familiar
    checks.append(CheckResult(
        level=CheckLevel.FIELD,
        passed=passed,
        detail=f"Device {device_id} {'is' if actual_familiar else 'is not'} in baseline known devices; claimed familiar={claimed_familiar}"
    ))
    
    return checks


def verify_context_exists(claim: Claim, conn) -> List[CheckResult]:
    """Verify CONTEXT_EXISTS claim: record exists AND optional user_id/record_type match."""
    checks = []
    structured = claim.structured
    
    if not structured or "record_id" not in structured:
        checks.append(CheckResult(
            level=CheckLevel.CITATION,
            passed=False,
            detail="Malformed structured field: missing record_id"
        ))
        return checks
    
    record_id = structured["record_id"]
    
    # Check citation
    checks.append(verify_citation_record(record_id, conn))
    
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, record_type FROM context_records WHERE record_id = ?", (record_id,))
    row = cursor.fetchone()
    
    if not row:
        checks.append(CheckResult(
            level=CheckLevel.CITATION,
            passed=False,
            detail=f"Record {record_id} not found"
        ))
        return checks
    
    # Check user_id if provided
    if "user_id" in structured:
        expected_user = structured["user_id"]
        actual_user = row["user_id"]
        passed = actual_user == expected_user
        checks.append(CheckResult(
            level=CheckLevel.FIELD,
            passed=passed,
            detail=f"Record user_id: expected={expected_user}, actual={actual_user}"
        ))
    
    # Check record_type if provided
    if "record_type" in structured:
        expected_type = structured["record_type"]
        actual_type = row["record_type"]
        passed = actual_type == expected_type
        checks.append(CheckResult(
            level=CheckLevel.FIELD,
            passed=passed,
            detail=f"Record record_type: expected={expected_type}, actual={actual_type}"
        ))
    
    return checks


def verify_claim(
    claim: Claim,
    conn,
    baseline_cutoff: str,
    retrieved_event_ids: Optional[Set[str]] = None,
    retrieved_record_ids: Optional[Set[str]] = None,
) -> ClaimVerification:
    """Verify a single claim."""
    checks = []
    status = VerificationStatus.NOT_CHECKABLE
    explanation = ""
    
    # Provenance check
    provenance_ok = None
    if retrieved_event_ids is not None or retrieved_record_ids is not None:
        all_cited = set(claim.cited_event_ids) | set(claim.cited_record_ids)
        all_retrieved = (retrieved_event_ids or set()) | (retrieved_record_ids or set())
        if all_cited:
            provenance_ok = all_cited.issubset(all_retrieved)
    
    if claim.claim_type == ClaimType.EVENT_EXISTS:
        checks = verify_event_exists(claim, conn)
        if checks and all(c.passed for c in checks):
            status = VerificationStatus.VERIFIED
        else:
            status = VerificationStatus.FAILED
        explanation = "Event existence verified" if status == VerificationStatus.VERIFIED else "Event not found"
    
    elif claim.claim_type == ClaimType.FIELD_VALUE:
        checks = verify_field_value(claim, conn)
        if checks and all(c.passed for c in checks):
            status = VerificationStatus.VERIFIED
        else:
            status = VerificationStatus.FAILED
        explanation = "Field value matches" if status == VerificationStatus.VERIFIED else "Field value mismatch or malformed"
    
    elif claim.claim_type == ClaimType.ORDER:
        checks = verify_order(claim, conn)
        if checks and all(c.passed for c in checks):
            status = VerificationStatus.VERIFIED
        else:
            status = VerificationStatus.FAILED
        explanation = "Order correct" if status == VerificationStatus.VERIFIED else "Order incorrect or malformed"
    
    elif claim.claim_type == ClaimType.DEVICE_FAMILIARITY:
        checks = verify_device_familiarity(claim, conn, baseline_cutoff)
        if checks and all(c.passed for c in checks):
            status = VerificationStatus.VERIFIED
        else:
            status = VerificationStatus.FAILED
        explanation = "Device familiarity matches baseline" if status == VerificationStatus.VERIFIED else "Device familiarity mismatch or malformed"
    
    elif claim.claim_type == ClaimType.CONTEXT_EXISTS:
        checks = verify_context_exists(claim, conn)
        if checks and all(c.passed for c in checks):
            status = VerificationStatus.VERIFIED
        else:
            status = VerificationStatus.FAILED
        explanation = "Context record exists and matches" if status == VerificationStatus.VERIFIED else "Context record not found or mismatch"
    
    elif claim.claim_type in (ClaimType.INTERPRETATION, ClaimType.HYPOTHESIS, ClaimType.MISSING_EVIDENCE):
        status = VerificationStatus.NOT_CHECKABLE
        explanation = "Interpretive validity is not machine-checkable; shown as the model's interpretation."
        checks = []  # No checks for interpretive claims
    
    else:
        # Unknown claim type - treat as not checkable
        status = VerificationStatus.NOT_CHECKABLE
        explanation = f"Unknown claim type: {claim.claim_type}"
    
    return ClaimVerification(
        claim_id=claim.claim_id,
        claim_text=claim.text,
        claim_type=claim.claim_type,
        status=status,
        checks_run=checks,
        explanation=explanation,
        provenance_ok=provenance_ok,
    )


def verify_investigation(
    investigation: Investigation,
    conn,
    baseline_cutoff: str,
    retrieved_event_ids: Optional[List[str]] = None,
    retrieved_record_ids: Optional[List[str]] = None,
) -> VerificationReport:
    """
    Verify all claims in an investigation.
    Returns VerificationReport with per-claim results and summary.
    """
    # Handle empty lists properly - they should be converted to empty sets, not None
    retrieved_eids = set(retrieved_event_ids) if retrieved_event_ids is not None else None
    retrieved_rids = set(retrieved_record_ids) if retrieved_record_ids is not None else None
    
    verifications = []
    for claim in investigation.claims:
        ver = verify_claim(claim, conn, baseline_cutoff, retrieved_eids, retrieved_rids)
        verifications.append(ver)
    
    # Compute summary
    status_counts = {s: 0 for s in VerificationStatus}
    for v in verifications:
        status_counts[v.status] += 1
    
    # Citation rate
    total_cited = sum(len(c.cited_event_ids) + len(c.cited_record_ids) for c in investigation.claims)
    verified_cited = 0
    for v in verifications:
        if v.status == VerificationStatus.VERIFIED:
            verified_cited += len(v.checks_run) if v.checks_run else 0
    
    valid_citation_rate = verified_cited / total_cited if total_cited > 0 else 1.0
    
    # Unsupported claim rate = FAILED / (VERIFIED + FAILED)
    checked = status_counts[VerificationStatus.VERIFIED] + status_counts[VerificationStatus.FAILED]
    unsupported_claim_rate = status_counts[VerificationStatus.FAILED] / checked if checked > 0 else 0.0
    
    summary = {
        "status_counts": {s.value: c for s, c in status_counts.items()},
        "valid_citation_rate": valid_citation_rate,
        "unsupported_claim_rate": unsupported_claim_rate,
        "total_claims": len(verifications),
    }
    
    return VerificationReport(
        claim_verifications=verifications,
        summary=summary,
    )


def print_verification_report(report: VerificationReport) -> None:
    """Print a readable table of verification results."""
    print("=" * 100)
    print(f"{'Claim':<6} {'Status':<14} {'Type':<20} {'Explanation'}")
    print("-" * 100)
    
    for v in report.claim_verifications:
        status_str = v.status.value
        type_str = v.claim_type.value
        print(f"{v.claim_id:<6} {status_str:<14} {type_str:<20} {v.explanation}")
        for check in v.checks_run:
            check_str = "[OK]" if check.passed else "[FAIL]"
            print(f"  {check_str} [{check.level.value}] {check.detail}")
        if v.provenance_ok is not None:
            prov_str = "OK" if v.provenance_ok else "WARNING: cited ID not retrieved"
            print(f"  Provenance: {prov_str}")
    
    print("-" * 100)
    print(f"Summary: {json.dumps(report.summary, indent=2)}")


if __name__ == "__main__":
    # Quick test
    from src.scenario import create_demo_scenario, build_session
    from src.investigator import run_investigation
    
    scenario = create_demo_scenario()
    session = build_session(scenario)
    
    # Run investigation
    result = run_investigation(session, scenario["question"], llm_mode="json")
    
    if result.investigation:
        # Verify
        conn = session.conn
        report = verify_investigation(
            result.investigation,
            conn,
            scenario["baseline_cutoff"],
            result.retrieved_event_ids,
            result.retrieved_record_ids,
        )
        print_verification_report(report)
    
    session.conn.close()