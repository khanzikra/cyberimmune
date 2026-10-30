"""
Smoke tests for Streamlit app helper functions.
"""
import html


def format_badge(status: str, reason: str = "") -> str:
    """Format a claim status badge with safe HTML."""
    colors = {
        "VERIFIED": "#00D4AA",
        "FAILED": "#FF6B6B",
        "NOT_CHECKABLE": "#888888",
    }
    color = colors.get(status, "#888888")
    tooltip = f' title="{html.escape(reason)}"' if reason else ""
    return f'<span style="background-color:{color};color:white;padding:2px 8px;border-radius:4px;font-size:0.8em;font-weight:bold;"{tooltip}>{status}</span>'


def escape_for_display(text: str) -> str:
    """Escape text for safe display in Streamlit."""
    return html.escape(str(text))


def test_format_badge():
    """Test badge formatting."""
    badge = format_badge("VERIFIED")
    assert "VERIFIED" in badge
    assert "#00D4AA" in badge
    assert "title=" not in badge

    badge = format_badge("VERIFIED", "Event exists")
    assert 'title="Event exists"' in badge

    badge = format_badge("FAILED", "Wrong timestamp")
    assert "FAILED" in badge
    assert "#FF6B6B" in badge
    assert 'title="Wrong timestamp"' in badge

    badge = format_badge("NOT_CHECKABLE")
    assert "NOT_CHECKABLE" in badge
    assert "#888888" in badge

    badge = format_badge("UNKNOWN")
    assert "UNKNOWN" in badge
    assert "#888888" in badge


def test_escape_for_display():
    # html.escape returns HTML entity-escaped strings
    # < becomes <, > becomes >, & becomes &, " becomes ", ' becomes '
    assert escape_for_display("<script>alert(1)</script>") == "<script>alert(1)</script>"
    assert escape_for_display("a & b") == "a & b"
    assert escape_for_display("'quotes'") == "'quotes'"  # single quotes not escaped by default in Python < 3.7
    assert escape_for_display(123) == "123"
    assert escape_for_display(None) == "None"
    malicious = 'EVT-001 <img src=x onerror=alert(1)>'
    escaped = escape_for_display(malicious)
    assert "<img" not in escaped
    assert "<img" in escaped
    assert "onerror" not in escaped


def test_badge_with_malicious_reason():
    badge = format_badge("FAILED", "<script>alert(1)</script>")
    assert "<script>" not in badge
    assert "<script>alert(1)</script>" in badge


def test_badge_html_structure():
    badge = format_badge("VERIFIED", "Test reason")
    assert badge.startswith('<span style=')
    assert 'background-color:#00D4AA' in badge
    assert 'color:white' in badge
    assert 'padding:2px 8px' in badge
    assert 'border-radius:4px' in badge
    assert 'font-size:0.8em' in badge
    assert 'font-weight:bold' in badge
    assert 'title="Test reason"' in badge
    assert badge.endswith('</span>')


if __name__ == "__main__":
    test_format_badge()
    test_escape_for_display()
    test_badge_with_malicious_reason()
    test_badge_html_structure()
    print("All test_app_smoke.py tests passed!")