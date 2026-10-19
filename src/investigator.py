"""
Investigation loop: model calls tools, Python validates and runs them, returns structured Investigation.
"""
import json
import argparse
import sys
from typing import List, Dict, Any, Optional, Literal
from pathlib import Path
import re

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.llm_client import LLMClient
from src.event_tools import ToolSession, dispatch, TOOL_SCHEMAS
from src.scenario import load_scenario, build_session
from src.prompts import SYSTEM_PROMPT, SYSTEM_PROMPT_VERSION
from src.schemas import (
    Investigation,
    InvestigationResult,
    ToolAction,
    FinalAction,
    Claim,
)


MAX_ROUNDS = 6
MAX_TOOL_CALLS = 10
MAX_RESULT_CHARS = 6000


def _truncate_result(obj: Any, max_chars: int = MAX_RESULT_CHARS) -> str:
    """Convert tool result to string, truncate if needed."""
    text = json.dumps(obj, default=str)
    if len(text) > max_chars:
        return text[:max_chars] + "... [truncated]"
    return text


def _strip_markdown_fences(text: str) -> str:
    """Remove markdown code fences if present."""
    # Remove ```json ... ``` or ``` ... ```
    pattern = r"^```(?:json)?\s*(.*?)\s*```$"
    match = re.match(pattern, text.strip(), re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()


def _parse_final_json(text: str) -> Dict[str, Any]:
    """Parse the model's final JSON output."""
    text = _strip_markdown_fences(text)
    return json.loads(text)


def _validate_investigation(data: Dict[str, Any]) -> Investigation:
    """Validate investigation with pydantic, return Investigation or raise."""
    return Investigation(**data)


def _run_native_mode(
    client: LLMClient,
    session: ToolSession,
    question: str,
    model_name: str,
) -> InvestigationResult:
    """Run investigation with native tool calling."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]

    audit_steps = []
    rounds_used = 0
    tool_calls_used = 0
    retrieved_event_ids = set()
    retrieved_record_ids = set()

    while rounds_used < MAX_ROUNDS and tool_calls_used < MAX_TOOL_CALLS:
        rounds_used += 1

        # Call the model
        response = client.chat(messages, tools=TOOL_SCHEMAS, temperature=0.0)

        # Log model response summary
        if response.get("tool_calls"):
            for tc in response["tool_calls"]:
                audit_steps.append({
                    "step": "model_tool_call",
                    "tool": tc["function"]["name"],
                    "args": json.loads(tc["function"]["arguments"]),
                })
        else:
            audit_steps.append({
                "step": "model_response",
                "content_preview": (response.get("content") or "")[:200],
            })

        # Add model response to messages
        messages.append(response)

        # Handle tool calls
        if response.get("tool_calls"):
            for tc in response["tool_calls"]:
                if tool_calls_used >= MAX_TOOL_CALLS:
                    break

                tool_name = tc["function"]["name"]
                try:
                    args = json.loads(tc["function"]["arguments"])
                except json.JSONDecodeError as e:
                    error_msg = f"Invalid tool arguments JSON: {e}"
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": json.dumps({"ok": False, "error": error_msg}),
                    })
                    audit_steps.append({
                        "step": "tool_error",
                        "tool": tool_name,
                        "error": error_msg,
                    })
                    continue

                # Dispatch tool
                result = dispatch(session, tool_name, args)

                # Track retrieved IDs
                if result.get("ok") and "data" in result:
                    data = result["data"]
                    if isinstance(data, list):
                        for item in data:
                            if "event_id" in item:
                                retrieved_event_ids.add(item["event_id"])
                            if "record_id" in item:
                                retrieved_record_ids.add(item["record_id"])

                # Add tool result as tool message
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": _truncate_result(result),
                })

                audit_steps.append({
                    "step": "tool_result",
                    "tool": tool_name,
                    "ok": result.get("ok"),
                    "row_count": len(result.get("data", [])) if isinstance(result.get("data"), list) else (1 if result.get("ok") else 0),
                    "error": result.get("error"),
                })

                tool_calls_used += 1

            continue  # Next round

        # No tool calls - model should output final JSON
        content = response.get("content", "")
        if not content:
            audit_steps.append({"step": "error", "error": "Model returned empty content"})
            return InvestigationResult(
                investigation=None,
                status="failed",
                audit_steps=audit_steps,
                rounds_used=rounds_used,
                retrieved_event_ids=list(retrieved_event_ids),
                retrieved_record_ids=list(retrieved_record_ids),
                model_name=model_name,
                system_prompt_version=SYSTEM_PROMPT_VERSION,
            )

        # Try to parse and validate
        try:
            inv_data = _parse_final_json(content)
            investigation = _validate_investigation(inv_data)
        except (json.JSONDecodeError, Exception) as e:
            # Track validation attempts
            validation_attempts = sum(1 for s in audit_steps if s.get("step") == "validation_error") + 1
            
            audit_steps.append({
                "step": "validation_error",
                "error": str(e),
                "attempt": validation_attempts,
            })
            
            if validation_attempts >= 2:
                # Second failure - give up
                return InvestigationResult(
                    investigation=None,
                    status="validation_error",
                    audit_steps=audit_steps,
                    rounds_used=rounds_used,
                    retrieved_event_ids=list(retrieved_event_ids),
                    retrieved_record_ids=list(retrieved_record_ids),
                    model_name=model_name,
                    system_prompt_version=SYSTEM_PROMPT_VERSION,
                )
            
            # First failure - retry once
            messages.append({
                "role": "user",
                "content": f"Invalid JSON or validation error: {e}. Return corrected JSON only, no extra text.",
            })
            # Continue to next round
            continue

        # Success
        return InvestigationResult(
            investigation=investigation,
            status="success",
            audit_steps=audit_steps,
            rounds_used=rounds_used,
            retrieved_event_ids=list(retrieved_event_ids),
            retrieved_record_ids=list(retrieved_record_ids),
            model_name=model_name,
            system_prompt_version=SYSTEM_PROMPT_VERSION,
        )

    # Limits reached
    return InvestigationResult(
        investigation=None,
        status="limit_reached",
        audit_steps=audit_steps,
        rounds_used=rounds_used,
        retrieved_event_ids=list(retrieved_event_ids),
        retrieved_record_ids=list(retrieved_record_ids),
        model_name=model_name,
        system_prompt_version=SYSTEM_PROMPT_VERSION,
    )


def _run_json_mode(
    client: LLMClient,
    session: ToolSession,
    question: str,
    model_name: str,
) -> InvestigationResult:
    """Run investigation with JSON fallback mode."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT + "\n\nJSON FALLBACK MODE: Reply with exactly one JSON object per turn:\n- {\"action\":\"tool\",\"tool\":\"<name>\",\"args\":{...}} to call a tool\n- {\"action\":\"final\",\"investigation\":{...}} to finish\nNo other text."},
        {"role": "user", "content": question},
    ]

    audit_steps = []
    rounds_used = 0
    tool_calls_used = 0
    retrieved_event_ids = set()
    retrieved_record_ids = set()

    while rounds_used < MAX_ROUNDS and tool_calls_used < MAX_TOOL_CALLS:
        rounds_used += 1

        response = client.chat(messages, tools=None, temperature=0.0)
        content = response.get("content", "")

        if not content:
            audit_steps.append({"step": "error", "error": "Model returned empty content"})
            return InvestigationResult(
                investigation=None,
                status="failed",
                audit_steps=audit_steps,
                rounds_used=rounds_used,
                retrieved_event_ids=list(retrieved_event_ids),
                retrieved_record_ids=list(retrieved_record_ids),
                model_name=model_name,
                system_prompt_version=SYSTEM_PROMPT_VERSION,
            )

        # Parse action
        try:
            action_data = json.loads(content)
            action_type = action_data.get("action")
            if action_type == "tool":
                action = ToolAction(**action_data)
            elif action_type == "final":
                action = FinalAction(**action_data)
            else:
                raise ValueError(f"Unknown action type: {action_type}")
        except (json.JSONDecodeError, Exception) as e:
            audit_steps.append({
                "step": "parse_error",
                "error": f"Failed to parse action JSON: {e}",
            })
            messages.append({
                "role": "user",
                "content": f"Invalid JSON. Must be exactly one JSON object: {{\"action\":\"tool\",...}} or {{\"action\":\"final\",...}} Error: {e}",
            })
            continue

        messages.append({"role": "assistant", "content": content})

        if action.action == "tool":
            if tool_calls_used >= MAX_TOOL_CALLS:
                audit_steps.append({"step": "limit", "error": "Max tool calls reached"})
                break

            audit_steps.append({
                "step": "model_tool_call",
                "tool": action.tool,
                "args": action.args,
            })

            result = dispatch(session, action.tool, action.args)

            if result.get("ok") and "data" in result:
                data = result["data"]
                if isinstance(data, list):
                    for item in data:
                        if "event_id" in item:
                            retrieved_event_ids.add(item["event_id"])
                        if "record_id" in item:
                            retrieved_record_ids.add(item["record_id"])

            messages.append({
                "role": "user",
                "content": _truncate_result(result),
            })

            audit_steps.append({
                "step": "tool_result",
                "tool": action.tool,
                "ok": result.get("ok"),
                "row_count": len(result.get("data", [])) if isinstance(result.get("data"), list) else (1 if result.get("ok") else 0),
                "error": result.get("error"),
            })

            tool_calls_used += 1

        elif action.action == "final":
            validation_attempts = sum(1 for s in audit_steps if s.get("step") == "validation_error") + 1
            
            try:
                investigation = _validate_investigation(action.investigation.model_dump())
            except Exception as e:
                audit_steps.append({
                    "step": "validation_error",
                    "error": str(e),
                    "attempt": validation_attempts,
                })
                
                if validation_attempts >= 2:
                    return InvestigationResult(
                        investigation=None,
                        status="validation_error",
                        audit_steps=audit_steps,
                        rounds_used=rounds_used,
                        retrieved_event_ids=list(retrieved_event_ids),
                        retrieved_record_ids=list(retrieved_record_ids),
                        model_name=model_name,
                        system_prompt_version=SYSTEM_PROMPT_VERSION,
                    )
                
                messages.append({
                    "role": "user",
                    "content": f"Validation error: {e}. Return corrected JSON only.",
                })
                continue

            return InvestigationResult(
                investigation=investigation,
                status="success",
                audit_steps=audit_steps,
                rounds_used=rounds_used,
                retrieved_event_ids=list(retrieved_event_ids),
                retrieved_record_ids=list(retrieved_record_ids),
                model_name=model_name,
                system_prompt_version=SYSTEM_PROMPT_VERSION,
            )

    return InvestigationResult(
        investigation=None,
        status="limit_reached",
        audit_steps=audit_steps,
        rounds_used=rounds_used,
        retrieved_event_ids=list(retrieved_event_ids),
        retrieved_record_ids=list(retrieved_record_ids),
        model_name=model_name,
        system_prompt_version=SYSTEM_PROMPT_VERSION,
    )


def run_investigation(
    session: ToolSession,
    question: str,
    llm: Optional[LLMClient] = None,
    mode: Literal["native", "json"] = "native",
) -> InvestigationResult:
    """
    Run the investigation loop.
    Returns InvestigationResult with investigation (or None), status, audit_steps, etc.
    """
    if llm is None:
        llm = LLMClient()

    model_name = llm.model

    if mode == "json":
        return _run_json_mode(llm, session, question, model_name)
    else:
        return _run_native_mode(llm, session, question, model_name)


def main():
    parser = argparse.ArgumentParser(description="Run investigation on a scenario")
    parser.add_argument("--scenario", required=True, help="Path to scenario JSON")
    parser.add_argument("--out", required=True, help="Output JSON path")
    parser.add_argument("--mode", choices=["native", "json"], default="native", help="Tool calling mode")
    args = parser.parse_args()

    # Load scenario
    scenario = load_scenario(args.scenario)
    question = scenario["question"]

    # Build session
    session = build_session(scenario)

    # Run investigation
    print(f"Running investigation (mode={args.mode})...")
    result = run_investigation(session, question, mode=args.mode)

    # Save result
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(result.model_dump(mode="json"), f, indent=2)

    print(f"Status: {result.status}")
    print(f"Rounds: {result.rounds_used}")
    print(f"Tool calls: {sum(1 for s in result.audit_steps if s.get('step') == 'model_tool_call')}")
    print(f"Saved to {args.out}")


if __name__ == "__main__":
    main()