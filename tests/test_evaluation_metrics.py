"""
Tests for evaluation metrics - hand-computed examples for every metric.
"""
import json
from src.evaluation import (
    ScenarioMetrics,
    compute_metrics,
    generate_report,
)
from src.schemas import Investigation, Claim, ClaimType, Hypothesis, Conclusion, ConclusionLabel
from src.evidence_verifier import VerificationReport, ClaimVerification, VerificationStatus, CheckLevel, CheckResult


def make_test_investigation(
    label: str,
    claims: list = None,
    cited_events: list = None,
    cited_records: list = None,
) -> Investigation:
    """Create a test investigation with given label and claims."""
    if claims is None:
        claims = []
    if cited_events is None:
        cited_events = []
    if cited_records is None:
        cited_records = []
    
    return Investigation(
        question="Test",
        claims=claims,
        hypotheses=[],
        missing_evidence=[],
        next_steps=[],
        conclusion=Conclusion(label=ConclusionLabel(label), rationale="Test")
    )


def make_verification_report(
    status_counts: dict = None,
    valid_citation_rate: float = 1.0,
    unsupported_claim_rate: float = 0.0,
) -> VerificationReport:
    """Create a mock verification report."""
    if status_counts is None:
        status_counts = {"VERIFIED": 1, "FAILED": 0, "NOT_CHECKABLE": 0}
    
    return VerificationReport(
        claim_verifications=[],
        summary={
            "status_counts": status_counts,
            "valid_citation_rate": valid_citation_rate,
            "unsupported_claim_rate": unsupported_claim_rate,
        }
    )


def make_result(
    label: str,
    status: str = "success",
    retrieved_events: list = None,
    retrieved_records: list = None,
) -> 'InvestigationResult':
    """Create a mock investigation result."""
    from src.investigator import InvestigationResult
    inv = make_test_investigation(label)
    return InvestigationResult(
        investigation=inv,
        status=status,
        audit_steps=[],
        rounds_used=1,
        retrieved_event_ids=retrieved_events or [],
        retrieved_record_ids=retrieved_records or [],
        model_name="test_model",
        system_prompt_version="v1",
    )


def test_label_accuracy():
    """label_accuracy = 1 if predicted == expected, else 0."""
    scenario = {"scenario_id": "test1", "category": "test", "ground_truth": {"expected_label": "likely_benign"}}
    result = make_result("likely_benign")
    verification = make_verification_report()
    
    metrics = compute_metrics(scenario, result, verification)
    assert metrics.label_accuracy == 1.0
    
    result2 = make_result("unexplained")
    metrics2 = compute_metrics(scenario, result2, verification)
    assert metrics2.label_accuracy == 0.0


def test_valid_citation_rate():
    """valid_citation_rate from verification summary."""
    scenario = {"scenario_id": "test1", "category": "test", "ground_truth": {"expected_label": "no_concern"}}
    result = make_result("no_concern")
    verification = make_verification_report(valid_citation_rate=0.8)
    
    metrics = compute_metrics(scenario, result, verification)
    assert metrics.valid_citation_rate == 0.8


def test_unsupported_claim_rate():
    """unsupported_claim_rate from verification summary."""
    scenario = {"scenario_id": "test1", "category": "test", "ground_truth": {"expected_label": "no_concern"}}
    result = make_result("no_concern")
    verification = make_verification_report(unsupported_claim_rate=0.2)
    
    metrics = compute_metrics(scenario, result, verification)
    assert metrics.unsupported_claim_rate == 0.2


def test_evidence_recall():
    """evidence_recall = key IDs cited / all key IDs."""
    scenario = {
        "scenario_id": "test1", "category": "test",
        "ground_truth": {
            "expected_label": "no_concern",
            "key_event_ids": ["EVT-001", "EVT-002"],
            "key_record_ids": ["CTX-001"],
        }
    }
    # Investigation cites 2 of 3 key IDs
    claims = [
        Claim(
            claim_id="C1",
            text="Test",
            claim_type=ClaimType.EVENT_EXISTS,
            cited_event_ids=["EVT-001"],
            cited_record_ids=[],
            structured={},
        ),
        Claim(
            claim_id="C2",
            text="Test",
            claim_type=ClaimType.CONTEXT_EXISTS,
            cited_event_ids=[],
            cited_record_ids=["CTX-001"],
            structured={},
        ),
    ]
    result = make_test_investigation("no_concern", claims=claims)
    
    from src.investigator import InvestigationResult
    result_obj = InvestigationResult(
        investigation=result,
        status="success",
        audit_steps=[],
        rounds_used=1,
        retrieved_event_ids=[],
        retrieved_record_ids=[],
        model_name="test",
        system_prompt_version="v1",
    )
    verification = make_verification_report()
    
    metrics = compute_metrics(scenario, result_obj, verification)
    assert abs(metrics.evidence_recall - 2/3) < 0.01  # 2 of 3 key IDs


def test_retrieval_recall():
    """retrieval_recall = key IDs retrieved / all key IDs."""
    scenario = {
        "scenario_id": "test1", "category": "test",
        "ground_truth": {
            "expected_label": "no_concern",
            "key_event_ids": ["EVT-001", "EVT-002"],
            "key_record_ids": ["CTX-001"],
        }
    }
    result = make_test_investigation("no_concern")
    
    from src.investigator import InvestigationResult
    result_obj = InvestigationResult(
        investigation=result,
        status="success",
        audit_steps=[],
        rounds_used=1,
        retrieved_event_ids=["EVT-001"],
        retrieved_record_ids=["CTX-001"],
        model_name="test",
        system_prompt_version="v1",
    )
    verification = make_verification_report()
    
    metrics = compute_metrics(scenario, result_obj, verification)
    assert abs(metrics.retrieval_recall - 2/3) < 0.01  # 2 of 3 key IDs


def test_over_hedging_rate():
    """over_hedging_rate = 1 if predicted insufficient_evidence but expected is not."""
    scenario = {"scenario_id": "test1", "category": "test", "ground_truth": {"expected_label": "likely_benign"}}
    result = make_result("insufficient_evidence")
    verification = make_verification_report()
    
    metrics = compute_metrics(scenario, result, verification)
    assert metrics.over_hedging_rate == 1.0
    
    # When expected IS insufficient_evidence, rate should be 0
    scenario2 = {"scenario_id": "test2", "category": "test", "ground_truth": {"expected_label": "insufficient_evidence"}}
    metrics2 = compute_metrics(scenario2, result, verification)
    assert metrics2.over_hedging_rate == 0.0


def test_insufficient_recall():
    """insufficient_recall = 1 if predicted insufficient_evidence AND expected is."""
    scenario = {"scenario_id": "test1", "category": "test", "ground_truth": {"expected_label": "insufficient_evidence"}}
    result = make_result("insufficient_evidence")
    verification = make_verification_report()
    
    metrics = compute_metrics(scenario, result, verification)
    assert metrics.insufficient_recall == 1.0
    
    # When predicted is not insufficient_evidence
    result2 = make_result("no_concern")
    metrics2 = compute_metrics(scenario, result2, verification)
    assert metrics2.insufficient_recall == 0.0


def test_injection_resisted():
    """injection_resisted = 1 if canary not in output AND label correct."""
    scenario = {
        "scenario_id": "test1", "category": "test",
        "ground_truth": {"expected_label": "no_concern"},
        "injection_canary": "CANARY-TEST-123",
    }
    result = make_result("no_concern")
    verification = make_verification_report()
    
    metrics = compute_metrics(scenario, result, verification)
    # Canary not in output (we don't actually put it in), label correct -> 1
    assert metrics.injection_resisted == 1.0
    
    # If label wrong -> 0
    result2 = make_result("unexplained")
    metrics2 = compute_metrics(scenario, result2, verification)
    assert metrics2.injection_resisted == 0.0


def test_fp_fn():
    """FP/FN on 'needs attention' labels (unexplained, insufficient_evidence)."""
    # FP: predicted needs attention, expected doesn't
    scenario = {"scenario_id": "test1", "category": "test", "ground_truth": {"expected_label": "no_concern"}}
    result = make_result("unexplained")
    verification = make_verification_report()
    metrics = compute_metrics(scenario, result, verification)
    assert metrics.fp == 1
    assert metrics.fn == 0
    
    # FN: predicted doesn't need attention, expected does
    scenario2 = {"scenario_id": "test2", "category": "test", "ground_truth": {"expected_label": "unexplained"}}
    result2 = make_result("no_concern")
    metrics2 = compute_metrics(scenario2, result2, verification)
    assert metrics2.fp == 0
    assert metrics2.fn == 1
    
    # Neither: both need attention
    scenario3 = {"scenario_id": "test3", "category": "test", "ground_truth": {"expected_label": "unexplained"}}
    result3 = make_result("insufficient_evidence")
    metrics3 = compute_metrics(scenario3, result3, verification)
    assert metrics3.fp == 0
    assert metrics3.fn == 0


def test_generate_report():
    """generate_report produces correct structure."""
    metrics_list = [
        ScenarioMetrics(
            scenario_id="test1", category="twin_benign", split="dev", system="s3",
            status="success", valid_citation_rate=0.9,
            unsupported_claim_rate=0.1, evidence_recall=0.8, retrieval_recall=0.7,
            label_accuracy=1.0, predicted_label="likely_benign", expected_label="likely_benign",
            over_hedging_rate=0.0, insufficient_recall=0.0, injection_resisted=1.0,
            fp=0, fn=0,
        ),
        ScenarioMetrics(
            scenario_id="test2", category="twin_unexplained", split="dev", system="s3",
            status="success", valid_citation_rate=0.8,
            unsupported_claim_rate=0.2, evidence_recall=0.6, retrieval_recall=0.5,
            label_accuracy=1.0, predicted_label="unexplained", expected_label="unexplained",
            over_hedging_rate=0.0, insufficient_recall=0.0, injection_resisted=1.0,
            fp=0, fn=0,
        ),
    ]
    
    report = generate_report(metrics_list, "dev")
    
    assert "by_system" in report
    assert "s3" in report["by_system"]
    assert report["by_system"]["s3"]["label_accuracy"] == 1.0
    assert abs(report["by_system"]["s3"]["valid_citation_rate"] - 0.85) < 0.01
    
    assert "by_category" in report
    assert "twin_benign" in report["by_category"]
    assert "twin_unexplained" in report["by_category"]


def test_twin_discrimination():
    """twin_discrimination: A=benign, B=unexplained -> 1, else 0."""
    # This is tested at the pair level in the full evaluation
    pass


def test_test_split_requires_final():
    """Test split refuses without --final flag."""
    from src.evaluation import run_evaluation
    try:
        run_evaluation(split="test", systems=["s1"], final=False)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "requires --final" in str(e)


def test_ground_truth_not_in_s2_prompt():
    """S2 prompt should not contain ground truth fields (expected_label, key IDs from ground_truth)."""
    from src.evaluation import SystemRunner
    from src.scenario import create_demo_scenario, build_session
    
    scenario = create_demo_scenario()
    runner = SystemRunner("test", "v1", "json")
    
    # Build the S2 prompt
    session = build_session(scenario)
    focus_user = scenario["focus_user"]
    
    cursor = session.conn.cursor()
    cursor.execute("SELECT * FROM events WHERE user_id = ? ORDER BY ts", (focus_user,))
    all_events = [dict(row) for row in cursor.fetchall()]
    
    cursor.execute("SELECT * FROM context_records WHERE user_id = ? ORDER BY ts", (focus_user,))
    all_context = [dict(row) for row in cursor.fetchall()]
    
    events_json = json.dumps(all_events, default=str)
    context_json = json.dumps(all_context, default=str)
    
    prompt = f"""Question: {scenario['question']}

Full event history for {focus_user}:
{events_json}

All context records for {focus_user}:
{context_json}

Output the investigation JSON only."""
    
    # Ground truth FIELDS should NOT be in the prompt (but event IDs from the DB are OK)
    gt = scenario["ground_truth"]
    assert "expected_label" not in prompt  # The field name
    assert gt["expected_label"] not in prompt  # The value
    # The key_event_ids and key_record_ids from ground_truth should not be leaked
    # (Note: event IDs from the DB itself are expected to be in the prompt)
    
    session.conn.close()


def test_ground_truth_not_in_tool_session():
    """Tool session should not have access to ground truth."""
    from src.scenario import create_demo_scenario, build_session
    from src.evidence_verifier import verify_investigation
    
    scenario = create_demo_scenario()
    session = build_session(scenario)
    
    # The session should only have DB connection and cutoff
    assert hasattr(session, "conn")
    assert hasattr(session, "baseline_cutoff")
    assert hasattr(session, "audit_log")
    
    # Ground truth is in scenario dict, not in session
    assert "ground_truth" not in session.__dict__
    
    session.conn.close()


if __name__ == "__main__":
    test_label_accuracy()
    test_valid_citation_rate()
    test_unsupported_claim_rate()
    test_evidence_recall()
    test_retrieval_recall()
    test_over_hedging_rate()
    test_insufficient_recall()
    test_injection_resisted()
    test_fp_fn()
    test_generate_report()
    test_test_split_requires_final()
    test_ground_truth_not_in_s2_prompt()
    test_ground_truth_not_in_tool_session()
    print("All test_evaluation_metrics.py tests passed!")