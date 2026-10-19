"""
Tests for investigator loop using a FAKE LLM (no network, no credits).
"""
import os
import json
from pathlib import Path
import sys

# Set fake env before importing modules that read them
os.environ.setdefault("NEBIUS_API_KEY", "fake-key-for-testing")
os.environ.setdefault("NEBIUS_BASE_URL", "https://fake.example.com/v1")
os.environ.setdefault("NEBIUS_MODEL", "fake-model")

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.investigator import run_investigation
from src.scenario import load_scenario, build_session
from src.event_tools import ToolSession
from src.schemas import Investigation, InvestigationResult


class FakeLLMClient:
    """Fake LLM client that returns scripted responses."""

    def __init__(self, responses):
        self.responses = responses
        self.call_count = 0
        self.model = "fake-model"

    def chat(self, messages, tools=None, temperature=0.0, max_tokens=4000):
        if self.call_count >= len(self.responses):
            return {"role": "assistant", "content": "", "tool_calls": None}
        resp = self.responses[self.call_count]
        self.call_count += 1
        return resp


def make_test_session():
    """Create a test session with demo scenario."""
    scenario = load_scenario("data/demo_scenario.json")
    session = build_session(scenario)
    return session


def test_scripted_tool_call_then_valid_final_json():
    """Scripted tool call then valid final JSON => success, audit log has steps."""
    tool_call_resp = {
        "role": "assistant",
        "content": None,
        "tool_calls": [{
            "id": "call_1",
            "type": "function",
            "function": {
                "name": "query_events",
                "arguments": '{"user_id": "user_01", "event_type": "login", "limit": 5}'
            }
        }]
    }

    final_json = {
        "question": "test question",
        "claims": [{
            "claim_id": "C1",
            "text": "User logged in",
            "claim_type": "EVENT_EXISTS",
            "cited_event_ids": ["EVT-990001"],
            "cited_record_ids": [],
            "structured": {"event_id": "EVT-990001"},
            "supports": [],
            "contradicts": [],
            "limitations": ""
        }],
        "hypotheses": [],
        "missing_evidence": [],
        "next_steps": ["Review with user"],
        "conclusion": {"label": "unexplained", "rationale": "Need more info"}
    }

    final_resp = {
        "role": "assistant",
        "content": json.dumps(final_json),
        "tool_calls": None
    }

    fake_llm = FakeLLMClient([tool_call_resp, final_resp])
    session = make_test_session()

    result = run_investigation(session, "test question", llm=fake_llm, mode="native")

    assert result.status == "success"
    assert result.investigation is not None
    assert len(result.investigation.claims) == 1
    assert result.rounds_used >= 1

    tool_call_steps = [s for s in result.audit_steps if s.get("step") == "model_tool_call"]
    assert len(tool_call_steps) == 1
    assert tool_call_steps[0]["tool"] == "query_events"


def test_invalid_tool_args_error_returned_to_model():
    """Invalid tool args => error returned to the model, loop continues."""
    tool_call_resp = {
        "role": "assistant",
        "content": None,
        "tool_calls": [{
            "id": "call_1",
            "type": "function",
            "function": {
                "name": "query_events",
                "arguments": '{"event_type": "login"}'
            }
        }]
    }

    tool_call_resp2 = {
        "role": "assistant",
        "content": None,
        "tool_calls": [{
            "id": "call_2",
            "type": "function",
            "function": {
                "name": "query_events",
                "arguments": '{"user_id": "user_01", "limit": 3}'
            }
        }]
    }

    final_json = {
        "question": "test question",
        "claims": [{
            "claim_id": "C1",
            "text": "User logged in",
            "claim_type": "EVENT_EXISTS",
            "cited_event_ids": ["EVT-990001"],
            "cited_record_ids": [],
            "structured": {"event_id": "EVT-990001"},
            "supports": [],
            "contradicts": [],
            "limitations": ""
        }],
        "hypotheses": [],
        "missing_evidence": [],
        "next_steps": ["Review with user"],
        "conclusion": {"label": "unexplained", "rationale": "Need more info"}
    }

    final_resp = {
        "role": "assistant",
        "content": json.dumps(final_json),
        "tool_calls": None
    }

    fake_llm = FakeLLMClient([tool_call_resp, tool_call_resp2, final_resp])
    session = make_test_session()

    result = run_investigation(session, "test question", llm=fake_llm, mode="native")

    assert result.status == "success"
    assert result.investigation is not None

    error_steps = [s for s in result.audit_steps if s.get("step") == "tool_result" and s.get("ok") is False]
    assert len(error_steps) == 1
    # The error comes from dispatch catching the TypeError
    assert "missing 1 required positional argument: 'user_id'" in error_steps[0]["error"]


def test_model_never_stops_ends_at_limits():
    """Model that never stops => ends at round/tool-call limits with status limit_reached."""
    tool_call_resp = {
        "role": "assistant",
        "content": None,
        "tool_calls": [{
            "id": "call_x",
            "type": "function",
            "function": {
                "name": "query_events",
                "arguments": '{"user_id": "user_01", "limit": 1}'
            }
        }]
    }

    fake_llm = FakeLLMClient([tool_call_resp] * 15)
    session = make_test_session()

    result = run_investigation(session, "test question", llm=fake_llm, mode="native")

    assert result.status == "limit_reached"
    assert result.investigation is None
    assert result.rounds_used <= 6


def test_invalid_final_json_twice_failed_result():
    """Invalid final JSON twice => failed result, no crash."""
    tool_call_resp = {
        "role": "assistant",
        "content": None,
        "tool_calls": [{
            "id": "call_1",
            "type": "function",
            "function": {
                "name": "query_events",
                "arguments": '{"user_id": "user_01", "limit": 3}'
            }
        }]
    }

    invalid_resp = {
        "role": "assistant",
        "content": "not valid json {{{",
        "tool_calls": None
    }

    invalid_resp2 = {
        "role": "assistant",
        "content": "still not json",
        "tool_calls": None
    }

    fake_llm = FakeLLMClient([tool_call_resp, invalid_resp, invalid_resp2])
    session = make_test_session()

    result = run_investigation(session, "test question", llm=fake_llm, mode="native")

    assert result.status == "validation_error"
    assert result.investigation is None

    val_errors = [s for s in result.audit_steps if s.get("step") == "validation_error"]
    assert len(val_errors) >= 1


def test_json_fallback_mode():
    """JSON fallback mode works with scripted replies."""
    tool_action = {
        "action": "tool",
        "tool": "query_events",
        "args": {"user_id": "user_01", "limit": 3}
    }

    final_json = {
        "question": "test question",
        "claims": [{
            "claim_id": "C1",
            "text": "User logged in",
            "claim_type": "EVENT_EXISTS",
            "cited_event_ids": ["EVT-990001"],
            "cited_record_ids": [],
            "structured": {"event_id": "EVT-990001"},
            "supports": [],
            "contradicts": [],
            "limitations": ""
        }],
        "hypotheses": [],
        "missing_evidence": [],
        "next_steps": ["Review with user"],
        "conclusion": {"label": "unexplained", "rationale": "Need more info"}
    }

    final_action = {
        "action": "final",
        "investigation": final_json
    }

    fake_llm = FakeLLMClient([
        {"role": "assistant", "content": json.dumps(tool_action), "tool_calls": None},
        {"role": "assistant", "content": json.dumps(final_action), "tool_calls": None},
    ])
    session = make_test_session()

    result = run_investigation(session, "test question", llm=fake_llm, mode="json")

    assert result.status == "success"
    assert result.investigation is not None
    assert len(result.investigation.claims) == 1


def test_no_api_key_in_result():
    """Result contains no API key text (fake key in env never appears)."""
    tool_call_resp = {
        "role": "assistant",
        "content": None,
        "tool_calls": [{
            "id": "call_1",
            "type": "function",
            "function": {
                "name": "query_events",
                "arguments": '{"user_id": "user_01", "limit": 3}'
            }
        }]
    }

    final_json = {
        "question": "test question",
        "claims": [{
            "claim_id": "C1",
            "text": "User logged in",
            "claim_type": "EVENT_EXISTS",
            "cited_event_ids": ["EVT-990001"],
            "cited_record_ids": [],
            "structured": {"event_id": "EVT-990001"},
            "supports": [],
            "contradicts": [],
            "limitations": ""
        }],
        "hypotheses": [],
        "missing_evidence": [],
        "next_steps": ["Review with user"],
        "conclusion": {"label": "unexplained", "rationale": "Need more info"}
    }

    final_resp = {
        "role": "assistant",
        "content": json.dumps(final_json),
        "tool_calls": None
    }

    fake_llm = FakeLLMClient([tool_call_resp, final_resp])
    session = make_test_session()

    result = run_investigation(session, "test question", llm=fake_llm, mode="native")

    result_json = result.model_dump_json()
    assert "fake-key-for-testing" not in result_json
    assert "NEBIUS_API_KEY" not in result_json


def test_investigation_result_serialization():
    """InvestigationResult serializes correctly without secrets."""
    tool_call_resp = {
        "role": "assistant",
        "content": None,
        "tool_calls": [{
            "id": "call_1",
            "type": "function",
            "function": {
                "name": "query_events",
                "arguments": '{"user_id": "user_01", "limit": 3}'
            }
        }]
    }

    final_json = {
        "question": "test question",
        "claims": [{
            "claim_id": "C1",
            "text": "User logged in",
            "claim_type": "EVENT_EXISTS",
            "cited_event_ids": ["EVT-990001"],
            "cited_record_ids": [],
            "structured": {"event_id": "EVT-990001"},
            "supports": [],
            "contradicts": [],
            "limitations": ""
        }],
        "hypotheses": [],
        "missing_evidence": [],
        "next_steps": ["Review with user"],
        "conclusion": {"label": "unexplained", "rationale": "Need more info"}
    }

    final_resp = {
        "role": "assistant",
        "content": json.dumps(final_json),
        "tool_calls": None
    }

    fake_llm = FakeLLMClient([tool_call_resp, final_resp])
    session = make_test_session()

    result = run_investigation(session, "test question", llm=fake_llm, mode="native")

    data = result.model_dump(mode="json")
    assert "investigation" in data
    assert "status" in data
    assert "audit_steps" in data
    assert "rounds_used" in data
    assert "retrieved_event_ids" in data
    assert "retrieved_record_ids" in data
    assert "model_name" in data
    assert "system_prompt_version" in data


if __name__ == "__main__":
    test_scripted_tool_call_then_valid_final_json()
    print("✓ test_scripted_tool_call_then_valid_final_json")
    test_invalid_tool_args_error_returned_to_model()
    print("✓ test_invalid_tool_args_error_returned_to_model")
    test_model_never_stops_ends_at_limits()
    print("✓ test_model_never_stops_ends_at_limits")
    test_invalid_final_json_twice_failed_result()
    print("✓ test_invalid_final_json_twice_failed_result")
    test_json_fallback_mode()
    print("✓ test_json_fallback_mode")
    test_no_api_key_in_result()
    print("✓ test_no_api_key_in_result")
    test_investigation_result_serialization()
    print("✓ test_investigation_result_serialization")
    print("\nAll investigator tests passed!")