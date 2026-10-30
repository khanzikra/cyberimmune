"""
Tests for evidence verifier using a table of claims with a small in-memory DB.
"""
import tempfile
import os
import sqlite3
from datetime import datetime, timezone

from src.database import connect, create_schema, insert_events, insert_context
from src.evidence_verifier import (
    verify_investigation,
    verify_claim,
    VerificationStatus,
    CheckLevel,
    CheckResult,
    ClaimVerification,
)
from src.schemas import Claim, ClaimType, Investigation, Hypothesis, Conclusion, ConclusionLabel


def create_test_db():
    """Create a test database with known data."""
    conn = connect(":memory:")
    create_schema(conn)
    
    # Events
    events = [
        # user_01 baseline events
        {
            "event_id": "EVT-000001",
            "ts": "2024-01-10T10:00:00Z",
            "user_id": "user_01",
            "event_type": "login",
            "device_id": "device_A",
            "resource": None,
            "source_ip": "10.0.0.1",
            "outcome": "success",
            "details": "Login",
        },
        {
            "event_id": "EVT-000002",
            "ts": "2024-01-10T11:00:00Z",
            "user_id": "user_01",
            "event_type": "resource_access",
            "device_id": "device_A",
            "resource": "email",
            "source_ip": "10.0.0.1",
            "outcome": "success",
            "details": "Accessed email",
        },
        {
            "event_id": "EVT-000003",
            "ts": "2024-01-10T12:00:00Z",
            "user_id": "user_01",
            "event_type": "login",
            "device_id": "device_A",
            "resource": None,
            "source_ip": "10.0.0.1",
            "outcome": "success",
            "details": "Login",
        },
        # user_02 event
        {
            "event_id": "EVT-000004",
            "ts": "2024-01-10T10:00:00Z",
            "user_id": "user_02",
            "event_type": "login",
            "device_id": "device_B",
            "resource": None,
            "source_ip": "10.0.0.2",
            "outcome": "success",
            "details": "User 02 login",
        },
    ]
    insert_events(conn, events)
    
    # Context records
    context = [
        {
            "record_id": "CTX-0001",
            "ts": "2024-01-09T10:00:00Z",
            "user_id": "user_01",
            "record_type": "it_ticket",
            "device_id": "device_A",
            "summary": "Device approved",
            "status": "approved",
        },
        {
            "record_id": "CTX-0002",
            "ts": "2024-01-09T11:00:00Z",
            "user_id": "user_02",
            "record_type": "approved_device",
            "device_id": "device_B",
            "summary": "Device approved",
            "status": "approved",
        },
    ]
    insert_context(conn, context)
    
    return conn


def make_investigation(claims):
    """Create a minimal investigation with the given claims."""
    return Investigation(
        question="Test",
        claims=claims,
        hypotheses=[],
        missing_evidence=[],
        next_steps=[],
        conclusion=Conclusion(label=ConclusionLabel.NO_CONCERN, rationale="Test")
    )


def test_true_claims_verified():
    """TRUE claims that must be VERIFIED: one per factual type."""
    conn = create_test_db()
    baseline_cutoff = "2024-01-15T00:00:00Z"
    
    claims = [
        # EVENT_EXISTS
        Claim(
            claim_id="C1",
            text="Event EVT-000001 exists",
            claim_type=ClaimType.EVENT_EXISTS,
            cited_event_ids=["EVT-000001"],
            cited_record_ids=[],
            structured={},
        ),
        # FIELD_VALUE
        Claim(
            claim_id="C2",
            text="Event EVT-000001 has device_id=device_A",
            claim_type=ClaimType.FIELD_VALUE,
            cited_event_ids=["EVT-000001"],
            cited_record_ids=[],
            structured={"event_id": "EVT-000001", "field": "device_id", "value": "device_A"},
        ),
        # ORDER
        Claim(
            claim_id="C3",
            text="EVT-000001 before EVT-000002",
            claim_type=ClaimType.ORDER,
            cited_event_ids=["EVT-000001", "EVT-000002"],
            cited_record_ids=[],
            structured={"first_event_id": "EVT-000001", "second_event_id": "EVT-000002"},
        ),
        # DEVICE_FAMILIARITY (device_A is in baseline for user_01)
        Claim(
            claim_id="C4",
            text="device_A is familiar for user_01",
            claim_type=ClaimType.DEVICE_FAMILIARITY,
            cited_event_ids=[],
            cited_record_ids=[],
            structured={"user_id": "user_01", "device_id": "device_A", "familiar": True},
        ),
        # CONTEXT_EXISTS
        Claim(
            claim_id="C5",
            text="Record CTX-0001 exists for user_01",
            claim_type=ClaimType.CONTEXT_EXISTS,
            cited_event_ids=[],
            cited_record_ids=["CTX-0001"],
            structured={"record_id": "CTX-0001", "user_id": "user_01", "record_type": "it_ticket"},
        ),
    ]
    
    inv = make_investigation(claims)
    report = verify_investigation(inv, conn, baseline_cutoff)
    
    for v in report.claim_verifications:
        assert v.status == VerificationStatus.VERIFIED, f"{v.claim_id} should be VERIFIED: {v.explanation}"
    
    conn.close()


def test_planted_false_claims_failed():
    """PLANTED FALSE claims that must be FAILED."""
    conn = create_test_db()
    baseline_cutoff = "2024-01-15T00:00:00Z"
    
    claims = [
        # 1. Nonexistent event ID
        Claim(
            claim_id="C1",
            text="Nonexistent event",
            claim_type=ClaimType.EVENT_EXISTS,
            cited_event_ids=["EVT-999999"],
            cited_record_ids=[],
            structured={},
        ),
        # 2. Right event wrong user
        Claim(
            claim_id="C2",
            text="Event EVT-000001 belongs to user_02",
            claim_type=ClaimType.FIELD_VALUE,
            cited_event_ids=["EVT-000001"],
            cited_record_ids=[],
            structured={"event_id": "EVT-000001", "field": "user_id", "value": "user_02"},
        ),
        # 3. Wrong timestamp
        Claim(
            claim_id="C3",
            text="Wrong timestamp",
            claim_type=ClaimType.FIELD_VALUE,
            cited_event_ids=["EVT-000001"],
            cited_record_ids=[],
            structured={"event_id": "EVT-000001", "field": "ts", "value": "2024-01-01T00:00:00Z"},
        ),
        # 4. Wrong device
        Claim(
            claim_id="C4",
            text="Wrong device",
            claim_type=ClaimType.FIELD_VALUE,
            cited_event_ids=["EVT-000001"],
            cited_record_ids=[],
            structured={"event_id": "EVT-000001", "field": "device_id", "value": "device_X"},
        ),
        # 5. Wrong resource
        Claim(
            claim_id="C5",
            text="Wrong resource",
            claim_type=ClaimType.FIELD_VALUE,
            cited_event_ids=["EVT-000002"],
            cited_record_ids=[],
            structured={"event_id": "EVT-000002", "field": "resource", "value": "github"},
        ),
        # 6. ORDER reversed
        Claim(
            claim_id="C6",
            text="EVT-000002 before EVT-000001 (reversed)",
            claim_type=ClaimType.ORDER,
            cited_event_ids=["EVT-000002", "EVT-000001"],
            cited_record_ids=[],
            structured={"first_event_id": "EVT-000002", "second_event_id": "EVT-000001"},
        ),
        # 7. DEVICE_FAMILIARITY wrong (claim familiar but not in baseline)
        Claim(
            claim_id="C7",
            text="device_X is familiar for user_01",
            claim_type=ClaimType.DEVICE_FAMILIARITY,
            cited_event_ids=[],
            cited_record_ids=[],
            structured={"user_id": "user_01", "device_id": "device_X", "familiar": True},
        ),
        # 8. Fake context record
        Claim(
            claim_id="C8",
            text="Fake context record",
            claim_type=ClaimType.CONTEXT_EXISTS,
            cited_event_ids=[],
            cited_record_ids=["CTX-999999"],
            structured={"record_id": "CTX-999999"},
        ),
        # 9. Context record belongs to another user
        Claim(
            claim_id="C9",
            text="CTX-0002 belongs to user_01",
            claim_type=ClaimType.CONTEXT_EXISTS,
            cited_event_ids=[],
            cited_record_ids=["CTX-0002"],
            structured={"record_id": "CTX-0002", "user_id": "user_01"},
        ),
        # 10. Malformed structured field (missing event_id)
        Claim(
            claim_id="C10",
            text="Malformed field value",
            claim_type=ClaimType.FIELD_VALUE,
            cited_event_ids=["EVT-000001"],
            cited_record_ids=[],
            structured={"field": "device_id", "value": "device_A"},  # missing event_id
        ),
    ]
    
    inv = make_investigation(claims)
    report = verify_investigation(inv, conn, baseline_cutoff)
    
    for v in report.claim_verifications:
        assert v.status == VerificationStatus.FAILED, f"{v.claim_id} should be FAILED: {v.explanation}"
    
    conn.close()


def test_interpretations_not_checkable():
    """Interpretations are NOT_CHECKABLE."""
    conn = create_test_db()
    baseline_cutoff = "2024-01-15T00:00:00Z"
    
    claims = [
        Claim(
            claim_id="C1",
            text="This is an interpretation",
            claim_type=ClaimType.INTERPRETATION,
            cited_event_ids=[],
            cited_record_ids=[],
            structured={},
        ),
        Claim(
            claim_id="C2",
            text="This is a hypothesis",
            claim_type=ClaimType.HYPOTHESIS,
            cited_event_ids=[],
            cited_record_ids=[],
            structured={},
        ),
        Claim(
            claim_id="C3",
            text="Missing evidence",
            claim_type=ClaimType.MISSING_EVIDENCE,
            cited_event_ids=[],
            cited_record_ids=[],
            structured={},
        ),
    ]
    
    inv = make_investigation(claims)
    report = verify_investigation(inv, conn, baseline_cutoff)
    
    for v in report.claim_verifications:
        assert v.status == VerificationStatus.NOT_CHECKABLE, f"{v.claim_id} should be NOT_CHECKABLE"
        assert "Interpretive validity is not machine-checkable" in v.explanation
    
    conn.close()


def test_failed_claims_remain_in_report():
    """Failed claims remain in the report."""
    conn = create_test_db()
    baseline_cutoff = "2024-01-15T00:00:00Z"
    
    claims = [
        Claim(
            claim_id="C1",
            text="Nonexistent",
            claim_type=ClaimType.EVENT_EXISTS,
            cited_event_ids=["EVT-999999"],
            cited_record_ids=[],
            structured={},
        ),
    ]
    
    inv = make_investigation(claims)
    report = verify_investigation(inv, conn, baseline_cutoff)
    
    assert len(report.claim_verifications) == 1
    assert report.claim_verifications[0].status == VerificationStatus.FAILED
    assert report.claim_verifications[0].claim_text == "Nonexistent"
    
    conn.close()


def test_summary_rates_correct():
    """Summary rates are correct on a hand-computed example."""
    conn = create_test_db()
    baseline_cutoff = "2024-01-15T00:00:00Z"
    
    # 3 VERIFIED, 2 FAILED, 1 NOT_CHECKABLE
    claims = [
        # VERIFIED
        Claim(claim_id="C1", text="T1", claim_type=ClaimType.EVENT_EXISTS, cited_event_ids=["EVT-000001"], cited_record_ids=[], structured={}),
        Claim(claim_id="C2", text="T2", claim_type=ClaimType.FIELD_VALUE, cited_event_ids=["EVT-000001"], cited_record_ids=[], structured={"event_id": "EVT-000001", "field": "device_id", "value": "device_A"}),
        Claim(claim_id="C3", text="T3", claim_type=ClaimType.ORDER, cited_event_ids=["EVT-000001", "EVT-000002"], cited_record_ids=[], structured={"first_event_id": "EVT-000001", "second_event_id": "EVT-000002"}),
        # FAILED
        Claim(claim_id="C4", text="F1", claim_type=ClaimType.EVENT_EXISTS, cited_event_ids=["EVT-999999"], cited_record_ids=[], structured={}),
        Claim(claim_id="C5", text="F2", claim_type=ClaimType.FIELD_VALUE, cited_event_ids=["EVT-000001"], cited_record_ids=[], structured={"event_id": "EVT-000001", "field": "device_id", "value": "device_X"}),
        # NOT_CHECKABLE
        Claim(claim_id="C6", text="I1", claim_type=ClaimType.INTERPRETATION, cited_event_ids=[], cited_record_ids=[], structured={}),
    ]
    
    inv = make_investigation(claims)
    report = verify_investigation(inv, conn, baseline_cutoff)
    
    summary = report.summary
    assert summary["status_counts"]["VERIFIED"] == 3
    assert summary["status_counts"]["FAILED"] == 2
    assert summary["status_counts"]["NOT_CHECKABLE"] == 1
    assert summary["total_claims"] == 6
    
    # unsupported_claim_rate = FAILED / (VERIFIED + FAILED) = 2 / (3 + 2) = 0.4
    assert abs(summary["unsupported_claim_rate"] - 0.4) < 0.001
    
    conn.close()


def test_provenance_warning():
    """Provenance warning appears when a cited event was never retrieved."""
    conn = create_test_db()
    baseline_cutoff = "2024-01-15T00:00:00Z"
    
    claims = [
        Claim(
            claim_id="C1",
            text="Event exists but was not retrieved",
            claim_type=ClaimType.EVENT_EXISTS,
            cited_event_ids=["EVT-000001"],
            cited_record_ids=[],
            structured={},
        ),
    ]
    
    inv = make_investigation(claims)
    # retrieved_event_ids does NOT include EVT-000001
    report = verify_investigation(inv, conn, baseline_cutoff, retrieved_event_ids=[], retrieved_record_ids=[])
    
    v = report.claim_verifications[0]
    assert v.provenance_ok is False, "Provenance should be False when cited ID not in retrieved sets"
    
    # Now with it retrieved
    report2 = verify_investigation(inv, conn, baseline_cutoff, retrieved_event_ids=["EVT-000001"], retrieved_record_ids=[])
    v2 = report2.claim_verifications[0]
    assert v2.provenance_ok is True, "Provenance should be True when cited ID is in retrieved sets"
    
    conn.close()


def test_malformed_structured_field_failed():
    """Factual claim with missing/malformed structured fields => FAILED."""
    conn = create_test_db()
    baseline_cutoff = "2024-01-15T00:00:00Z"
    
    claims = [
        Claim(
            claim_id="C1",
            text="Missing event_id in structured",
            claim_type=ClaimType.FIELD_VALUE,
            cited_event_ids=["EVT-000001"],
            cited_record_ids=[],
            structured={"field": "device_id", "value": "device_A"},  # missing event_id
        ),
    ]
    
    inv = make_investigation(claims)
    report = verify_investigation(inv, conn, baseline_cutoff)
    
    v = report.claim_verifications[0]
    assert v.status == VerificationStatus.FAILED
    assert "Malformed" in v.explanation or "malformed" in v.explanation.lower()
    
    conn.close()


def test_verify_claim_provenance_none_when_not_provided():
    """provenance_ok is None when retrieved sets not provided."""
    conn = create_test_db()
    baseline_cutoff = "2024-01-15T00:00:00Z"
    
    claim = Claim(
        claim_id="C1",
        text="Test",
        claim_type=ClaimType.EVENT_EXISTS,
        cited_event_ids=["EVT-000001"],
        cited_record_ids=[],
        structured={},
    )
    
    ver = verify_claim(claim, conn, baseline_cutoff, retrieved_event_ids=None, retrieved_record_ids=None)
    assert ver.provenance_ok is None
    
    conn.close()


if __name__ == "__main__":
    test_true_claims_verified()
    test_planted_false_claims_failed()
    test_interpretations_not_checkable()
    test_failed_claims_remain_in_report()
    test_summary_rates_correct()
    test_provenance_warning()
    test_malformed_structured_field_failed()
    test_verify_claim_provenance_none_when_not_provided()
    print("All test_verifier.py tests passed!")