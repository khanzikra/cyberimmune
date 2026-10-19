"""
Tests for the deterministic evidence verifier.
Uses a small in-memory DB with known data.
"""
import sqlite3
import tempfile
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.database import connect, create_schema, insert_events, insert_context
from src.evidence_verifier import verify_investigation, verify_claim, ClaimVerification
from src.schemas import (
    Claim, ClaimType, Investigation, Hypothesis, Conclusion, ConclusionLabel
)
from src.baseline import compute_baseline


def make_test_db():
    """Create a test database with controlled data."""
    conn = connect(":memory:")
    create_schema(conn)

    # Baseline cutoff: 2024-01-21
    cutoff = "2024-01-21T00:00:00Z"

    # User user_01 baseline events (before cutoff)
    events = [
        # 25 logins at hour 12 on device_A
        *[{
            "event_id": f"EVT-{i:06d}",
            "ts": f"2024-01-{d:02d}T12:00:00Z",
            "user_id": "user_01",
            "event_type": "login",
            "device_id": "device_A",
            "resource": None,
            "source_ip": "10.0.0.1",
            "outcome": "success",
            "details": "login",
        } for i, d in enumerate(range(1, 26), 1)],
        # 20 resource accesses to github
        *[{
            "event_id": f"EVT-{i:06d}",
            "ts": f"2024-01-{d:02d}T12:05:00Z",
            "user_id": "user_01",
            "event_type": "resource_access",
            "device_id": "device_A",
            "resource": "github",
            "source_ip": "10.0.0.1",
            "outcome": "success",
            "details": "access",
        } for i, d in enumerate(range(1, 21), 26)],
        # Focus window events (after cutoff)
        {
            "event_id": "EVT-990001",
            "ts": "2024-01-22T03:10:00Z",
            "user_id": "user_01",
            "event_type": "login",
            "device_id": "device_B",
            "resource": None,
            "source_ip": "10.0.0.2",
            "outcome": "success",
            "details": "unusual hour login",
        },
        {
            "event_id": "EVT-990002",
            "ts": "2024-01-22T03:11:00Z",
            "user_id": "user_01",
            "event_type": "resource_access",
            "device_id": "device_B",
            "resource": "k8s_cluster",
            "source_ip": "10.0.0.2",
            "outcome": "success",
            "details": "rare resource",
        },
        {
            "event_id": "EVT-990003",
            "ts": "2024-01-22T12:00:00Z",
            "user_id": "user_01",
            "event_type": "login",
            "device_id": "device_A",
            "resource": None,
            "source_ip": "10.0.0.1",
            "outcome": "success",
            "details": "normal login",
        },
    ]
    insert_events(conn, events)

    context = [
        {
            "record_id": "CTX-0001",
            "ts": "2024-01-21T14:00:00Z",
            "user_id": "user_01",
            "record_type": "it_ticket",
            "device_id": "device_B",
            "summary": "Laptop replacement approved",
            "status": "resolved",
        },
        {
            "record_id": "CTX-0002",
            "ts": "2024-01-22T02:00:00Z",
            "user_id": "user_01",
            "record_type": "approved_device",
            "device_id": "device_B",
            "summary": "Device B approved",
            "status": "active",
        },
    ]
    insert_context(conn, context)
    conn.commit()

    return conn, cutoff


def build_investigation(claims: list[Claim]) -> Investigation:
    """Helper to build an investigation with required fields."""
    return Investigation(
        question="Test investigation",
        claims=claims,
        hypotheses=[],
        missing_evidence=[],
        next_steps=[],
        conclusion=Conclusion(label=ConclusionLabel.UNEXPLAINED, rationale="Test"),
    )


# ===== TRUE CLAIMS (should VERIFY) =====

def test_true_event_exists():
    conn, cutoff = make_test_db()
    claim = Claim(
        claim_id="C1",
        text="Event EVT-990001 exists",
        claim_type=ClaimType.EVENT_EXISTS,
        cited_event_ids=["EVT-990001"],
        cited_record_ids=[],
        structured={"event_id": "EVT-990001"},
    )
    inv = build_investigation([claim])
    report = verify_investigation(inv, conn, cutoff)
    assert report.claim_verifications[0].status == "VERIFIED"
    conn.close()


def test_true_field_value():
    conn, cutoff = make_test_db()
    claim = Claim(
        claim_id="C1",
        text="Event EVT-990001 has user_id user_01",
        claim_type=ClaimType.FIELD_VALUE,
        cited_event_ids=["EVT-990001"],
        cited_record_ids=[],
        structured={"event_id": "EVT-990001", "field": "user_id", "value": "user_01"},
    )
    inv = build_investigation([claim])
    report = verify_investigation(inv, conn, cutoff)
    assert report.claim_verifications[0].status == "VERIFIED"
    conn.close()


def test_true_order():
    conn, cutoff = make_test_db()
    claim = Claim(
        claim_id="C1",
        text="EVT-990001 happened before EVT-990002",
        claim_type=ClaimType.ORDER,
        cited_event_ids=["EVT-990001", "EVT-990002"],
        cited_record_ids=[],
        structured={"first_event_id": "EVT-990001", "second_event_id": "EVT-990002"},
    )
    inv = build_investigation([claim])
    report = verify_investigation(inv, conn, cutoff)
    assert report.claim_verifications[0].status == "VERIFIED"
    conn.close()


def test_true_device_familiarity_false():
    conn, cutoff = make_test_db()
    # device_B is NOT in baseline for user_01
    claim = Claim(
        claim_id="C1",
        text="device_B is new for user_01",
        claim_type=ClaimType.DEVICE_FAMILIARITY,
        cited_event_ids=["EVT-990001"],
        cited_record_ids=[],
        structured={"user_id": "user_01", "device_id": "device_B", "familiar": False},
    )
    inv = build_investigation([claim])
    report = verify_investigation(inv, conn, cutoff)
    assert report.claim_verifications[0].status == "VERIFIED"
    conn.close()


def test_true_context_exists():
    conn, cutoff = make_test_db()
    claim = Claim(
        claim_id="C1",
        text="Context record CTX-0001 exists for user_01",
        claim_type=ClaimType.CONTEXT_EXISTS,
        cited_event_ids=[],
        cited_record_ids=["CTX-0001"],
        structured={"record_id": "CTX-0001", "user_id": "user_01", "record_type": "it_ticket"},
    )
    inv = build_investigation([claim])
    report = verify_investigation(inv, conn, cutoff)
    assert report.claim_verifications[0].status == "VERIFIED"
    conn.close()


# ===== PLANTED FALSE CLAIMS (should FAIL) =====

def test_false_nonexistent_event():
    conn, cutoff = make_test_db()
    claim = Claim(
        claim_id="C1",
        text="Nonexistent event exists",
        claim_type=ClaimType.EVENT_EXISTS,
        cited_event_ids=["EVT-NONEXISTENT"],
        cited_record_ids=[],
        structured={"event_id": "EVT-NONEXISTENT"},
    )
    inv = build_investigation([claim])
    report = verify_investigation(inv, conn, cutoff)
    assert report.claim_verifications[0].status == "FAILED"
    conn.close()


def test_false_wrong_user():
    conn, cutoff = make_test_db()
    # EVT-990001 belongs to user_01, claim it belongs to user_02
    claim = Claim(
        claim_id="C1",
        text="Event belongs to user_02",
        claim_type=ClaimType.FIELD_VALUE,
        cited_event_ids=["EVT-990001"],
        cited_record_ids=[],
        structured={"event_id": "EVT-990001", "field": "user_id", "value": "user_02"},
    )
    inv = build_investigation([claim])
    report = verify_investigation(inv, conn, cutoff)
    assert report.claim_verifications[0].status == "FAILED"
    conn.close()


def test_false_wrong_timestamp():
    conn, cutoff = make_test_db()
    claim = Claim(
        claim_id="C1",
        text="Wrong timestamp",
        claim_type=ClaimType.FIELD_VALUE,
        cited_event_ids=["EVT-990001"],
        cited_record_ids=[],
        structured={"event_id": "EVT-990001", "field": "ts", "value": "2024-01-22T04:00:00Z"},
    )
    inv = build_investigation([claim])
    report = verify_investigation(inv, conn, cutoff)
    assert report.claim_verifications[0].status == "FAILED"
    conn.close()


def test_false_wrong_device():
    conn, cutoff = make_test_db()
    claim = Claim(
        claim_id="C1",
        text="Wrong device",
        claim_type=ClaimType.FIELD_VALUE,
        cited_event_ids=["EVT-990001"],
        cited_record_ids=[],
        structured={"event_id": "EVT-990001", "field": "device_id", "value": "device_C"},
    )
    inv = build_investigation([claim])
    report = verify_investigation(inv, conn, cutoff)
    assert report.claim_verifications[0].status == "FAILED"
    conn.close()


def test_false_wrong_resource():
    conn, cutoff = make_test_db()
    claim = Claim(
        claim_id="C1",
        text="Wrong resource",
        claim_type=ClaimType.FIELD_VALUE,
        cited_event_ids=["EVT-990002"],
        cited_record_ids=[],
        structured={"event_id": "EVT-990002", "field": "resource", "value": "github"},
    )
    inv = build_investigation([claim])
    report = verify_investigation(inv, conn, cutoff)
    assert report.claim_verifications[0].status == "FAILED"
    conn.close()


def test_false_order_reversed():
    conn, cutoff = make_test_db()
    # EVT-990001 is at 03:10, EVT-990002 at 03:11 - claiming reverse
    claim = Claim(
        claim_id="C1",
        text="Reverse order",
        claim_type=ClaimType.ORDER,
        cited_event_ids=["EVT-990001", "EVT-990002"],
        cited_record_ids=[],
        structured={"first_event_id": "EVT-990002", "second_event_id": "EVT-990001"},
    )
    inv = build_investigation([claim])
    report = verify_investigation(inv, conn, cutoff)
    assert report.claim_verifications[0].status == "FAILED"
    conn.close()


def test_false_device_familiarity_wrong():
    conn, cutoff = make_test_db()
    # device_A IS in baseline, claim it's unfamiliar
    claim = Claim(
        claim_id="C1",
        text="device_A is unfamiliar",
        claim_type=ClaimType.DEVICE_FAMILIARITY,
        cited_event_ids=["EVT-990003"],
        cited_record_ids=[],
        structured={"user_id": "user_01", "device_id": "device_A", "familiar": False},
    )
    inv = build_investigation([claim])
    report = verify_investigation(inv, conn, cutoff)
    assert report.claim_verifications[0].status == "FAILED"
    conn.close()


def test_false_fake_context_record():
    conn, cutoff = make_test_db()
    claim = Claim(
        claim_id="C1",
        text="Fake context record",
        claim_type=ClaimType.CONTEXT_EXISTS,
        cited_event_ids=[],
        cited_record_ids=["CTX-FAKE"],
        structured={"record_id": "CTX-FAKE"},
    )
    inv = build_investigation([claim])
    report = verify_investigation(inv, conn, cutoff)
    assert report.claim_verifications[0].status == "FAILED"
    conn.close()


def test_false_context_wrong_user():
    conn, cutoff = make_test_db()
    # CTX-0001 belongs to user_01, claim it belongs to user_02
    claim = Claim(
        claim_id="C1",
        text="Context belongs to user_02",
        claim_type=ClaimType.CONTEXT_EXISTS,
        cited_event_ids=[],
        cited_record_ids=["CTX-0001"],
        structured={"record_id": "CTX-0001", "user_id": "user_02"},
    )
    inv = build_investigation([claim])
    report = verify_investigation(inv, conn, cutoff)
    assert report.claim_verifications[0].status == "FAILED"
    conn.close()


def test_false_malformed_structured():
    conn, cutoff = make_test_db()
    # Test that verifier catches missing structured fields by calling verify_claim directly
    # with a minimal claim-like object (bypassing Pydantic validation at creation)
    from src.evidence_verifier import verify_claim, ClaimVerification
    from types import SimpleNamespace

    # Create a claim-like object with empty structured
    claim_obj = SimpleNamespace(
        claim_id="C1",
        text="Malformed structured",
        claim_type=ClaimType.FIELD_VALUE,
        cited_event_ids=["EVT-990001"],
        cited_record_ids=[],
        structured={},  # empty - should fail
        model_dump=lambda: {
            "claim_id": "C1",
            "text": "Malformed structured",
            "claim_type": "FIELD_VALUE",
            "cited_event_ids": ["EVT-990001"],
            "cited_record_ids": [],
            "structured": {},
            "supports": [],
            "contradicts": [],
            "limitations": "",
        }
    )

    cv = verify_claim(claim_obj, conn, cutoff)
    assert cv.status == "FAILED"
    assert "malformed" in cv.explanation.lower() or "missing" in cv.explanation.lower()
    conn.close()


# ===== INTERPRETIVE CLAIMS (should be NOT_CHECKABLE) =====

def test_interpretation_not_checkable():
    conn, cutoff = make_test_db()
    claim = Claim(
        claim_id="C1",
        text="This looks suspicious",
        claim_type=ClaimType.INTERPRETATION,
        cited_event_ids=["EVT-990001"],
        cited_record_ids=[],
        structured={},
    )
    inv = build_investigation([claim])
    report = verify_investigation(inv, conn, cutoff)
    assert report.claim_verifications[0].status == "NOT_CHECKABLE"
    assert "Interpretive validity is not machine-checkable" in report.claim_verifications[0].explanation
    conn.close()


def test_hypothesis_not_checkable():
    conn, cutoff = make_test_db()
    claim = Claim(
        claim_id="C1",
        text="Maybe the user was compromised",
        claim_type=ClaimType.HYPOTHESIS,
        cited_event_ids=["EVT-990001"],
        cited_record_ids=[],
        structured={},
    )
    inv = build_investigation([claim])
    report = verify_investigation(inv, conn, cutoff)
    assert report.claim_verifications[0].status == "NOT_CHECKABLE"
    conn.close()


def test_missing_evidence_not_checkable():
    conn, cutoff = make_test_db()
    claim = Claim(
        claim_id="C1",
        text="We need more logs",
        claim_type=ClaimType.MISSING_EVIDENCE,
        cited_event_ids=[],
        cited_record_ids=[],
        structured={},
    )
    inv = build_investigation([claim])
    report = verify_investigation(inv, conn, cutoff)
    assert report.claim_verifications[0].status == "NOT_CHECKABLE"
    conn.close()


# ===== FAILED CLAIMS REMAIN IN REPORT =====

def test_failed_claims_remain_in_report():
    conn, cutoff = make_test_db()
    claims = [
        Claim(claim_id="C1", text="Good", claim_type=ClaimType.EVENT_EXISTS, cited_event_ids=["EVT-990001"], cited_record_ids=[], structured={"event_id": "EVT-990001"}),
        Claim(claim_id="C2", text="Bad", claim_type=ClaimType.EVENT_EXISTS, cited_event_ids=["EVT-FAKE"], cited_record_ids=[], structured={"event_id": "EVT-FAKE"}),
    ]
    inv = build_investigation(claims)
    report = verify_investigation(inv, conn, cutoff)
    assert len(report.claim_verifications) == 2
    assert report.claim_verifications[0].status == "VERIFIED"
    assert report.claim_verifications[1].status == "FAILED"
    conn.close()


# ===== SUMMARY RATES =====

def test_summary_rates():
    conn, cutoff = make_test_db()
    claims = [
        Claim(claim_id="C1", text="Good", claim_type=ClaimType.EVENT_EXISTS, cited_event_ids=["EVT-990001"], cited_record_ids=[], structured={"event_id": "EVT-990001"}),
        Claim(claim_id="C2", text="Bad", claim_type=ClaimType.EVENT_EXISTS, cited_event_ids=["EVT-FAKE"], cited_record_ids=[], structured={"event_id": "EVT-FAKE"}),
        Claim(claim_id="C3", text="Interp", claim_type=ClaimType.INTERPRETATION, cited_event_ids=[], cited_record_ids=[], structured={}),
    ]
    inv = build_investigation(claims)
    report = verify_investigation(inv, conn, cutoff)

    # valid_citation_rate = 1/2 = 0.5 (EVT-990001 exists, EVT-FAKE doesn't)
    # unsupported_claim_rate = 1/2 = 0.5 (1 failed / (1 verified + 1 failed))
    assert abs(report.summary["valid_citation_rate"] - 0.5) < 0.01
    assert abs(report.summary["unsupported_claim_rate"] - 0.5) < 0.01
    conn.close()


# ===== PROVENANCE WARNING =====

def test_provenance_warning():
    conn, cutoff = make_test_db()
    claim = Claim(
        claim_id="C1",
        text="Event not retrieved",
        claim_type=ClaimType.EVENT_EXISTS,
        cited_event_ids=["EVT-990001"],  # This exists but we'll say it wasn't retrieved
        cited_record_ids=[],
        structured={"event_id": "EVT-990001"},
    )
    inv = build_investigation([claim])
    # Provide empty retrieved sets
    report = verify_investigation(inv, conn, cutoff, retrieved_event_ids=[], retrieved_record_ids=[])
    assert report.claim_verifications[0].status == "VERIFIED"
    assert report.claim_verifications[0].provenance_ok is False
    conn.close()


if __name__ == "__main__":
    test_true_event_exists()
    print("✓ test_true_event_exists")
    test_true_field_value()
    print("✓ test_true_field_value")
    test_true_order()
    print("✓ test_true_order")
    test_true_device_familiarity_false()
    print("✓ test_true_device_familiarity_false")
    test_true_context_exists()
    print("✓ test_true_context_exists")

    test_false_nonexistent_event()
    print("✓ test_false_nonexistent_event")
    test_false_wrong_user()
    print("✓ test_false_wrong_user")
    test_false_wrong_timestamp()
    print("✓ test_false_wrong_timestamp")
    test_false_wrong_device()
    print("✓ test_false_wrong_device")
    test_false_wrong_resource()
    print("✓ test_false_wrong_resource")
    test_false_order_reversed()
    print("✓ test_false_order_reversed")
    test_false_device_familiarity_wrong()
    print("✓ test_false_device_familiarity_wrong")
    test_false_fake_context_record()
    print("✓ test_false_fake_context_record")
    test_false_context_wrong_user()
    print("✓ test_false_context_wrong_user")
    test_false_malformed_structured()
    print("✓ test_false_malformed_structured")

    test_interpretation_not_checkable()
    print("✓ test_interpretation_not_checkable")
    test_hypothesis_not_checkable()
    print("✓ test_hypothesis_not_checkable")
    test_missing_evidence_not_checkable()
    print("✓ test_missing_evidence_not_checkable")

    test_failed_claims_remain_in_report()
    print("✓ test_failed_claims_remain_in_report")
    test_summary_rates()
    print("✓ test_summary_rates")
    test_provenance_warning()
    print("✓ test_provenance_warning")

    print("\nAll verifier tests passed!")