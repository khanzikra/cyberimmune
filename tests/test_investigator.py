"""
Tests for investigator using a FAKE LLM (no network, no credits).
"""
import os
import json
from typing import List, Dict, Any, Optional
from unittest.mock import patch, MagicMock

from src.schemas import Investigation, InvestigationResult, Claim, ClaimType, Hypothesis, Conclusion, ConclusionLabel
from src.event_tools import ToolSession
from src.scenario import create_demo_scenario, build_session
from src.investigator import (
    run_investigation,
    parse_json_fallback,
    validate_investigation_json,
    truncate_result,
    sanitize_for_audit,
)


def create_mock_response(content: Optional[str], tool_calls: Optional[List[Dict[str, Any]]] = None):
    """Create a proper mock response object that extract_message can handle."""
    mock_message = MagicMock()
    mock_message.content = content
    
    if tool_calls:
        mock_tool_calls = []
        for tc in tool_calls:
            mock_tc = MagicMock()
            mock_tc.id = tc["id"]
            mock_tc.type = tc["type"]
            mock_func = MagicMock()
            mock_func.name = tc["function"]["name"]
            mock_func.arguments = tc["function"]["arguments"]
            mock_tc.function = mock_func
            mock_tool_calls.append(mock_tc)
        mock_message.tool_calls = mock_tool_calls
    else:
        mock_message.tool_calls = None
    
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    return mock_response


def test_fake_llm_scripted_tool_then_final():
    """Scripted tool call then valid final JSON => success."""
    scenario = create_demo_scenario()
    session = build_session(scenario)

    # Mock responses
    fake_responses = [
        # First call: tool call to get_baseline
        create_mock_response(None, [{
            "id": "call_1",
            "type": "function",
            "function": {"name": "get_baseline", "arguments": '{"user_id": "user_01"}'}
        }]),
        # Second call: final investigation
        create_mock_response(json.dumps({
            "question": scenario["question"],
            "claims": [
                {
                    "claim_id": "C1",
                    "text": "User logged in at unusual hour",
                    "claim_type": "EVENT_EXISTS",
                    "cited_event_ids": ["EVT-999001"],
                    "cited_record_ids": [],
                    "structured": {"event_id": "EVT-999001"},
                    "supports": [],
                    "contradicts": [],
                    "limitations": ""
                }
            ],
            "hypotheses": [
                {
                    "hypothesis_id": "H1",
                    "description": "Legitimate laptop replacement",
                    "supporting_claim_ids": ["C1"],
                    "contradicting_claim_ids": []
                }
            ],
            "missing_evidence": [],
            "next_steps": ["Human review of IT ticket"],
            "conclusion": {"label": "likely_benign", "rationale": "IT ticket explains new device"}
        }), None),
    ]

    call_idx = [0]

    def mock_chat(messages, tools=None, **kwargs):
        r = fake_responses[min(call_idx[0], len(fake_responses) - 1)]
        call_idx[0] += 1
        return r

    with patch('src.investigator.chat', mock_chat):
        result = run_investigation(session, scenario["question"], llm_mode="native")

    assert result.status == "success"
    assert result.investigation is not None
    assert len(result.audit_steps) > 0
    # Check audit has tool call and tool result
    tool_calls = [s for s in result.audit_steps if s.get("type") == "tool_call"]
    tool_results = [s for s in result.audit_steps if s.get("type") == "tool_result"]
    assert len(tool_calls) >= 1
    assert len(tool_results) >= 1

    session.conn.close()


def test_fake_llm_invalid_tool_args():
    """Invalid tool args => error returned to model, loop continues."""
    scenario = create_demo_scenario()
    session = build_session(scenario)

    # Mock responses: first call with bad args, second call with good args, third call final
    fake_responses = [
        # First: tool call with missing required user_id
        create_mock_response(None, [{
            "id": "call_1",
            "type": "function",
            "function": {"name": "query_events", "arguments": '{"event_type": "login"}'}
        }]),
        # Second: tool call with correct args
        create_mock_response(None, [{
            "id": "call_2",
            "type": "function",
            "function": {"name": "query_events", "arguments": '{"user_id": "user_01", "event_type": "login"}'}
        }]),
        # Third: final
        create_mock_response(json.dumps({
            "question": scenario["question"],
            "claims": [],
            "hypotheses": [],
            "missing_evidence": [],
            "next_steps": [],
            "conclusion": {"label": "no_concern", "rationale": "Test"}
        }), None),
    ]

    call_idx = [0]

    def mock_chat(messages, tools=None, **kwargs):
        r = fake_responses[min(call_idx[0], len(fake_responses) - 1)]
        call_idx[0] += 1
        return r

    with patch('src.investigator.chat', mock_chat):
        result = run_investigation(session, scenario["question"], llm_mode="native")

    assert result.status == "success"
    # Should have two tool calls (one failed, one succeeded)
    tool_results = [s for s in result.audit_steps if s.get("type") == "tool_result"]
    assert len(tool_results) == 2
    # First should have failed
    assert tool_results[0]["ok"] is False
    assert "Invalid user_id" in tool_results[0]["error"]
    # Second should succeed
    assert tool_results[1]["ok"] is True

    session.conn.close()


def test_fake_llm_never_stops():
    """Model that never stops calling tools => ends at limits with limit_reached."""
    scenario = create_demo_scenario()
    session = build_session(scenario)

    call_count = [0]

    def mock_chat(messages, tools=None, **kwargs):
        call_count[0] += 1
        return create_mock_response(None, [{
            "id": f"call_{call_count[0]}",
            "type": "function",
            "function": {"name": "get_baseline", "arguments": '{"user_id": "user_01"}'}
        }])

    with patch('src.investigator.chat', mock_chat):
        result = run_investigation(session, scenario["question"], llm_mode="native")

    assert result.status == "limit_reached"
    assert result.rounds_used == 6  # MAX_ROUNDS
    session.conn.close()


def test_fake_llm_invalid_final_json_twice():
    """Invalid final JSON twice => failed result, no crash."""
    scenario = create_demo_scenario()
    session = build_session(scenario)

    fake_responses = [
        # First: tool call
        create_mock_response(None, [{
            "id": "call_1",
            "type": "function",
            "function": {"name": "get_baseline", "arguments": '{"user_id": "user_01"}'}
        }]),
        # Second: invalid JSON
        create_mock_response("not valid json at all", None),
        # Third: still invalid JSON
        create_mock_response("{invalid json", None),
    ]

    call_idx = [0]

    def mock_chat(messages, tools=None, **kwargs):
        r = fake_responses[min(call_idx[0], len(fake_responses) - 1)]
        call_idx[0] += 1
        return r

    with patch('src.investigator.chat', mock_chat):
        result = run_investigation(session, scenario["question"], llm_mode="native")

    assert result.status == "validation_error"
    assert result.investigation is None
    session.conn.close()


def test_json_fallback_mode():
    """JSON fallback mode works with scripted replies."""
    scenario = create_demo_scenario()
    session = build_session(scenario)

    fake_responses = [
        # Tool action
        create_mock_response(json.dumps({"action": "tool", "tool": "get_baseline", "args": {"user_id": "user_01"}}), None),
        # Final action
        create_mock_response(json.dumps({
            "action": "final",
            "investigation": {
                "question": scenario["question"],
                "claims": [],
                "hypotheses": [],
                "missing_evidence": [],
                "next_steps": [],
                "conclusion": {"label": "no_concern", "rationale": "Test"}
            }
        }), None),
    ]

    call_idx = [0]

    def mock_chat(messages, tools=None, **kwargs):
        r = fake_responses[min(call_idx[0], len(fake_responses) - 1)]
        call_idx[0] += 1
        return r

    with patch('src.investigator.chat', mock_chat):
        result = run_investigation(session, scenario["question"], llm_mode="json")

    assert result.status == "success"
    assert result.investigation is not None
    session.conn.close()


def test_result_contains_no_api_key():
    """Result contains no API key text."""
    # Set a fake key in env
    os.environ["NVIDIA_API_KEY"] = "nvapi-FAKEKEY12345678901234567890"

    scenario = create_demo_scenario()
    session = build_session(scenario)

    fake_responses = [
        create_mock_response(json.dumps({
            "question": scenario["question"],
            "claims": [],
            "hypotheses": [],
            "missing_evidence": [],
            "next_steps": [],
            "conclusion": {"label": "no_concern", "rationale": "Test"}
        }), None),
    ]

    call_idx = [0]

    def mock_chat(messages, tools=None, **kwargs):
        r = fake_responses[min(call_idx[0], len(fake_responses) - 1)]
        call_idx[0] += 1
        return r

    with patch('src.investigator.chat', mock_chat):
        result = run_investigation(session, scenario["question"], llm_mode="native")

    # Check audit steps for any key leakage
    audit_str = json.dumps(result.audit_steps, default=str)
    assert "nvapi-FAKEKEY" not in audit_str
    assert "FAKEKEY" not in audit_str

    session.conn.close()
    del os.environ["NVIDIA_API_KEY"]


def test_parse_json_fallback():
    """Test JSON fallback parser."""
    # Valid JSON
    result = parse_json_fallback('{"action": "tool", "tool": "get_baseline", "args": {}}')
    assert result is not None
    assert result["action"] == "tool"

    # With markdown fences
    result = parse_json_fallback('```json\n{"action": "final", "investigation": {}}\n```')
    assert result is not None
    assert result["action"] == "final"

    # Invalid JSON
    result = parse_json_fallback("not json")
    assert result is None


def test_validate_investigation_json():
    """Test investigation JSON validation."""
    valid_json = json.dumps({
        "question": "Test",
        "claims": [
            {"claim_id": "C1", "text": "Test claim", "claim_type": "INTERPRETATION"}
        ],
        "hypotheses": [
            {"hypothesis_id": "H1", "description": "Test hypothesis"}
        ],
        "missing_evidence": [],
        "next_steps": [],
        "conclusion": {"label": "no_concern", "rationale": "Test"}
    })
    inv, err = validate_investigation_json(valid_json)
    assert err is None
    assert inv is not None
    assert len(inv.claims) == 1

    # Invalid - missing required field
    invalid_json = json.dumps({"question": "Test"})
    inv, err = validate_investigation_json(invalid_json)
    assert inv is None
    assert err is not None


def test_truncate_result():
    """Test result truncation."""
    small = {"a": 1}
    assert truncate_result(small) == small

    large = {"data": "x" * 10000}
    result = truncate_result(large, max_chars=100)
    assert isinstance(result, dict)
    assert "truncated" in result or len(json.dumps(result)) <= 200


def test_sanitize_for_audit():
    """Test secret sanitization."""
    data = {
        "api_key": "nvapi-SECRET12345678901234567890",
        "normal": "value",
        "nested": {"secret_key": "nvapi-ANOTHER12345678901234567890"}
    }
    sanitized = sanitize_for_audit(data)
    assert "nvapi-SECRET" not in str(sanitized)
    assert "nvapi-ANOTHER" not in str(sanitized)
    assert sanitized["normal"] == "value"


if __name__ == "__main__":
    test_parse_json_fallback()
    test_validate_investigation_json()
    test_truncate_result()
    test_sanitize_for_audit()
    print("Unit tests passed!")