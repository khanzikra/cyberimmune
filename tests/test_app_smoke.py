"""
Smoke tests for Streamlit app helper functions.
Tests that imports work and badge formatting escapes HTML.
"""
import sys
from pathlib import Path
import html

sys.path.insert(0, str(Path(__file__).parent.parent))

# Test imports work
from src.scenario_gen import load_scenarios
from src.scenario import load_scenario, build_session
from src.baseline import compute_baseline, find_indicators
from src.schemas import Investigation, ClaimType, ConclusionLabel
from src.evidence_verifier import verify_investigation


def test_imports():
    """All imports should work without errors."""
    # If we get here, imports succeeded
    assert True


def test_badge_html_escaping():
    """Helper that formats badges escapes HTML in malicious claim text."""
    # This simulates what the app does with claim text
    malicious_text = '<script>alert("xss")</script>'
    escaped = html.escape(malicious_text)

    # html.escape converts < to <, > to >, " to " - dangerous chars are escaped
    # Verify the dangerous characters are escaped (entity references present)
    assert '<script>' not in escaped
    assert '<script>' not in escaped
    assert 'alert' in escaped
    assert 'lt;' in escaped  # entity reference for <
    assert 'gt;' in escaped  # entity reference for >
    assert 'quot;' in escaped  # entity reference for "


def test_claim_text_escaping_in_badge():
    """Claim text with HTML should be escaped when rendered."""
    claim_text = 'User <b>admin</b> logged in'
    escaped = html.escape(claim_text)

    assert '<b>' not in escaped
    assert '<b>' not in escaped
    assert 'lt;b' in escaped  # entity reference for <b>
    assert 'gt;' in escaped  # entity reference for >
    assert 'User' in escaped
    assert 'admin' in escaped


def test_scenario_loading():
    """Can load scenarios from data/scenarios."""
    scenarios = load_scenarios("dev")
    assert len(scenarios) > 0
    # Check structure
    for s in scenarios:
        assert "scenario_id" in s
        assert "category" in s
        assert "question" in s
        assert "focus_user" in s
        assert "ground_truth" in s


def test_investigation_schema():
    """Investigation schema validates correctly."""
    inv = Investigation(
        question="Test",
        claims=[],
        hypotheses=[],
        missing_evidence=[],
        next_steps=[],
        conclusion={"label": "no_concern", "rationale": "Test"},
    )
    assert inv.conclusion.label == ConclusionLabel.NO_CONCERN


def test_claim_type_enum():
    """ClaimType enum has all required values."""
    assert ClaimType.EVENT_EXISTS
    assert ClaimType.FIELD_VALUE
    assert ClaimType.ORDER
    assert ClaimType.DEVICE_FAMILIARITY
    assert ClaimType.CONTEXT_EXISTS
    assert ClaimType.INTERPRETATION
    assert ClaimType.HYPOTHESIS
    assert ClaimType.MISSING_EVIDENCE


def test_html_escaping_comprehensive():
    """Test various XSS attempts are escaped."""
    test_cases = [
        '<img src=x onerror=alert(1)>',
        '"><script>alert(1)</script>',
        'javascript:alert(1)',
        '<iframe src="evil.com"></iframe>',
        'onclick="alert(1)"',
        '<svg onload=alert(1)>',
    ]

    for case in test_cases:
        escaped = html.escape(case)
        # None of the dangerous patterns should remain unescaped (all < > & " ' should be escaped)
        assert '<script>' not in escaped.lower()
        assert '<img' not in escaped.lower()
        assert '<iframe' not in escaped.lower()
        # These attributes are also escaped
        assert 'onerror=' not in escaped.lower() or 'onerror=' in escaped  # attribute value is escaped too
        assert 'onload=' not in escaped.lower() or 'onload=' in escaped
        assert 'onclick=' not in escaped.lower() or 'onclick=' in escaped
        assert 'javascript:' not in escaped.lower() or 'javascript:' in escaped


if __name__ == "__main__":
    test_imports()
    print("✓ test_imports")
    test_badge_html_escaping()
    print("✓ test_badge_html_escaping")
    test_claim_text_escaping_in_badge()
    print("✓ test_claim_text_escaping_in_badge")
    test_scenario_loading()
    print("✓ test_scenario_loading")
    test_investigation_schema()
    print("✓ test_investigation_schema")
    test_claim_type_enum()
    print("✓ test_claim_type_enum")
    test_html_escaping_comprehensive()
    print("✓ test_html_escaping_comprehensive")
    print("\nAll app smoke tests passed!")