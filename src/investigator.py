"""
Investigation loop: model calls tools, we validate and execute, model returns structured Investigation.
"""
import json
import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Literal
from datetime import datetime

from src.llm_client import chat, extract_message
from src.prompts import SYSTEM_PROMPT, JSON_FALLBACK_SYSTEM_PROMPT, build_messages
from src.event_tools import ToolSession, dispatch, TOOL_SCHEMAS
from src.schemas import Investigation, InvestigationResult, ConclusionLabel


MAX_ROUNDS = 6
MAX_TOOL_CALLS = 10
MAX_RESULT_CHARS = 6000


def truncate_result(data: Any, max_chars: int = MAX_RESULT_CHARS) -> Any:
    """Truncate tool result to max_chars. Preserves metadata fields (ok, error, row_count)."""
    if data is None:
        return None
    
    # If it's a tool result dict with 'data' list, truncate only the data array
    if isinstance(data, dict) and "data" in data and isinstance(data.get("data"), list):
        result_copy = data.copy()
        data_list = data["data"]
        
        # Try progressively smaller slices of the data list
        full_json = json.dumps(result_copy, ensure_ascii=False)
        if len(full_json) <= max_chars:
            return data
        
        # Binary search for max number of items to keep
        low, high = 0, len(data_list)
        best = data
        while low <= high:
            mid = (low + high) // 2
            test_result = result_copy.copy()
            test_result["data"] = data_list[:mid]
            test_json = json.dumps(test_result, ensure_ascii=False)
            if len(test_json) <= max_chars:
                best = test_result
                low = mid + 1
            else:
                high = mid - 1
        
        if best is not data:
            best["truncated"] = True
            best["original_count"] = len(data_list)
            best["returned_count"] = len(best["data"])
        return best
    
    # Fallback: truncate the whole JSON
    json_str = json.dumps(data, ensure_ascii=False)
    if len(json_str) <= max_chars:
        return data
    truncated = json_str[:max_chars] + "... [truncated]"
    try:
        return json.loads(truncated)
    except json.JSONDecodeError:
        return {"truncated": True, "original_length": len(json_str), "preview": truncated[:500]}


def sanitize_for_audit(obj: Any) -> Any:
    """Remove any potential secrets from audit log."""
    if isinstance(obj, dict):
        return {k: sanitize_for_audit(v) for k, v in obj.items() if "key" not in k.lower() and "secret" not in k.lower()}
    elif isinstance(obj, list):
        return [sanitize_for_audit(item) for item in obj]
    elif isinstance(obj, str):
        # Remove anything that looks like an API key
        return re.sub(r"nvapi-[A-Za-z0-9_-]{20,}", "[REDACTED]", obj)
    return obj


def parse_json_fallback(content: str) -> Optional[Dict[str, Any]]:
    """Parse JSON from model response (fallback mode).
    Handles both single JSON and multiple JSON objects (one per line)."""
    content = content.strip()
    # Remove markdown fences if present
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\n", "", content)
        content = re.sub(r"\n```$", "", content)
    
    # Try parsing as single JSON
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass
    
    # Try parsing each line as separate JSON (model may output multiple actions)
    for line in content.split('\n'):
        line = line.strip()
        if not line:
            continue
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            continue
    
    return None


def validate_investigation_json(json_str: str) -> tuple[Optional[Investigation], Optional[str]]:
    """Validate investigation JSON with pydantic."""
    # Strip markdown fences
    cleaned = json_str.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\n", "", cleaned)
        cleaned = re.sub(r"\n```$", "", cleaned)
    try:
        data = json.loads(cleaned)
        inv = Investigation.model_validate(data)
        return inv, None
    except Exception as e:
        return None, str(e)


def run_investigation(
    session: ToolSession,
    question: str,
    llm_mode: Literal["native", "json"] = "native",
    model_name: Optional[str] = None,
) -> InvestigationResult:
    """
    Run the investigation loop.
    Returns InvestigationResult with investigation, status, audit trail.
    """
    audit_steps = []
    retrieved_event_ids = set()
    retrieved_record_ids = set()
    tool_call_count = 0
    rounds = 0

    # Choose system prompt based on mode
    system_prompt = JSON_FALLBACK_SYSTEM_PROMPT if llm_mode == "json" else SYSTEM_PROMPT

    # Initial messages
    messages = build_messages(system_prompt, question)
    audit_steps.append({"type": "user_question", "question": question})

    while rounds < MAX_ROUNDS:
        rounds += 1
        audit_steps.append({"type": "round_start", "round": rounds})

        # Call the model
        try:
            response = chat(messages, tools=TOOL_SCHEMAS if llm_mode == "native" else None, timeout=120.0)
            msg = extract_message(response)
            audit_steps.append({"type": "model_response", "summary": {
                "has_content": msg["content"] is not None,
                "has_tool_calls": msg["tool_calls"] is not None,
                "tool_count": len(msg["tool_calls"]) if msg["tool_calls"] else 0,
            }})
        except Exception as e:
            audit_steps.append({"type": "model_error", "error": str(e)})
            return InvestigationResult(
                status="failed",
                audit_steps=audit_steps,
                rounds_used=rounds,
                retrieved_event_ids=list(retrieved_event_ids),
                retrieved_record_ids=list(retrieved_record_ids),
                model_name=model_name or os.getenv("NVIDIA_MODEL", ""),
                system_prompt_version="v1",
            )

        # Handle tool calls (native mode)
        if llm_mode == "native" and msg["tool_calls"]:
            if tool_call_count + len(msg["tool_calls"]) > MAX_TOOL_CALLS:
                audit_steps.append({"type": "limit_reached", "reason": "max_tool_calls"})
                return InvestigationResult(
                    status="limit_reached",
                    audit_steps=audit_steps,
                    rounds_used=rounds,
                    retrieved_event_ids=list(retrieved_event_ids),
                    retrieved_record_ids=list(retrieved_record_ids),
                    model_name=model_name or os.getenv("NVIDIA_MODEL", ""),
                    system_prompt_version="v1",
                )

            # Execute each tool call
            for tc in msg["tool_calls"]:
                tool_name = tc["function"]["name"]
                try:
                    args = json.loads(tc["function"]["arguments"])
                except json.JSONDecodeError:
                    args = {}

                tool_call_count += 1
                audit_steps.append({
                    "type": "tool_call",
                    "tool": tool_name,
                    "args": args,
                    "tool_call_id": tc["id"],
                })

                result = dispatch(session, tool_name, args)
                result = sanitize_for_audit(result)

                # Track retrieved IDs
                if result.get("ok") and isinstance(result.get("data"), list):
                    for item in result["data"]:
                        if "event_id" in item:
                            retrieved_event_ids.add(item["event_id"])
                        if "record_id" in item:
                            retrieved_record_ids.add(item["record_id"])

                # Truncate result
                result = truncate_result(result)

                audit_steps.append({
                    "type": "tool_result",
                    "tool": tool_name,
                    "ok": result.get("ok"),
                    "row_count": result.get("row_count", 0),
                    "error": result.get("error"),
                })

                # Add tool message to conversation
                messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [tc],
                })
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": json.dumps(result, ensure_ascii=False),
                })

            continue  # Next round

        # JSON fallback mode: parse action from content
        if llm_mode == "json" and msg["content"]:
            parsed = parse_json_fallback(msg["content"])
            if parsed:
                action = parsed.get("action")
                if action == "tool":
                    tool_name = parsed.get("tool")
                    args = parsed.get("args", {})
                    tool_call_count += 1
                    audit_steps.append({"type": "tool_call", "tool": tool_name, "args": args})

                    result = dispatch(session, tool_name, args)
                    result = sanitize_for_audit(result)

                    if result.get("ok") and isinstance(result.get("data"), list):
                        for item in result["data"]:
                            if "event_id" in item:
                                retrieved_event_ids.add(item["event_id"])
                            if "record_id" in item:
                                retrieved_record_ids.add(item["record_id"])

                    result = truncate_result(result)
                    audit_steps.append({"type": "tool_result", "tool": tool_name, "ok": result.get("ok"), "row_count": result.get("row_count", 0)})

                    # Add to messages for next round
                    messages.append({"role": "assistant", "content": msg["content"]})
                    messages.append({"role": "user", "content": json.dumps({"tool_result": result}, ensure_ascii=False)})
                    continue

                elif action == "final":
                    investigation_data = parsed.get("investigation")
                    if investigation_data:
                        inv, err = validate_investigation_json(json.dumps(investigation_data))
                        if err:
                            # Retry once with error
                            audit_steps.append({"type": "validation_error", "error": err})
                            messages.append({"role": "assistant", "content": msg["content"]})
                            messages.append({"role": "user", "content": f"Validation error: {err}. Return corrected JSON only."})
                            # Get one more response
                            try:
                                response2 = chat(messages, tools=None)
                                msg2 = extract_message(response2)
                                parsed2 = parse_json_fallback(msg2.get("content", ""))
                                if parsed2 and parsed2.get("action") == "final":
                                    inv2, err2 = validate_investigation_json(json.dumps(parsed2.get("investigation", {})))
                                    if err2:
                                        return InvestigationResult(
                                            status="validation_error",
                                            audit_steps=audit_steps,
                                            rounds_used=rounds,
                                            retrieved_event_ids=list(retrieved_event_ids),
                                            retrieved_record_ids=list(retrieved_record_ids),
                                            model_name=model_name or os.getenv("NVIDIA_MODEL", ""),
                                            system_prompt_version="v1",
                                        )
                                    return InvestigationResult(
                                        investigation=inv2,
                                        status="success",
                                        audit_steps=audit_steps,
                                        rounds_used=rounds,
                                        retrieved_event_ids=list(retrieved_event_ids),
                                        retrieved_record_ids=list(retrieved_record_ids),
                                        model_name=model_name or os.getenv("NVIDIA_MODEL", ""),
                                        system_prompt_version="v1",
                                    )
                            except Exception:
                                pass
                            return InvestigationResult(
                                status="validation_error",
                                audit_steps=audit_steps,
                                rounds_used=rounds,
                                retrieved_event_ids=list(retrieved_event_ids),
                                retrieved_record_ids=list(retrieved_record_ids),
                                model_name=model_name or os.getenv("NVIDIA_MODEL", ""),
                                system_prompt_version="v1",
                            )
                        return InvestigationResult(
                            investigation=inv,
                            status="success",
                            audit_steps=audit_steps,
                            rounds_used=rounds,
                            retrieved_event_ids=list(retrieved_event_ids),
                            retrieved_record_ids=list(retrieved_record_ids),
                            model_name=model_name or os.getenv("NVIDIA_MODEL", ""),
                            system_prompt_version="v1",
                        )

            # Force final prompt after 3 tool calls
            if tool_call_count >= 3:
                audit_steps.append({"type": "forced_final_prompt", "reason": "max_tool_calls_reached"})
                messages.append({"role": "user", "content": "You have gathered enough evidence. Output the final investigation JSON now with action:final."})
                continue

        # Native mode: check if model provided final answer (no tool calls, has content)
        if llm_mode == "native" and msg["content"] and not msg["tool_calls"]:
            inv, err = validate_investigation_json(msg["content"])
            if err:
                # Retry once with error
                audit_steps.append({"type": "validation_error", "error": err})
                messages.append({"role": "assistant", "content": msg["content"]})
                messages.append({"role": "user", "content": f"Validation error: {err}. Return corrected JSON only."})
                try:
                    response2 = chat(messages, tools=TOOL_SCHEMAS)
                    msg2 = extract_message(response2)
                    if msg2["content"]:
                        inv2, err2 = validate_investigation_json(msg2["content"])
                        if err2:
                            return InvestigationResult(
                                status="validation_error",
                                audit_steps=audit_steps,
                                rounds_used=rounds,
                                retrieved_event_ids=list(retrieved_event_ids),
                                retrieved_record_ids=list(retrieved_record_ids),
                                model_name=model_name or os.getenv("NVIDIA_MODEL", ""),
                                system_prompt_version="v1",
                            )
                        return InvestigationResult(
                            investigation=inv2,
                            status="success",
                            audit_steps=audit_steps,
                            rounds_used=rounds,
                            retrieved_event_ids=list(retrieved_event_ids),
                            retrieved_record_ids=list(retrieved_record_ids),
                            model_name=model_name or os.getenv("NVIDIA_MODEL", ""),
                            system_prompt_version="v1",
                        )
                except Exception:
                    pass
                return InvestigationResult(
                    status="validation_error",
                    audit_steps=audit_steps,
                    rounds_used=rounds,
                    retrieved_event_ids=list(retrieved_event_ids),
                    retrieved_record_ids=list(retrieved_record_ids),
                    model_name=model_name or os.getenv("NVIDIA_MODEL", ""),
                    system_prompt_version="v1",
                )
            return InvestigationResult(
                investigation=inv,
                status="success",
                audit_steps=audit_steps,
                rounds_used=rounds,
                retrieved_event_ids=list(retrieved_event_ids),
                retrieved_record_ids=list(retrieved_record_ids),
                model_name=model_name or os.getenv("NVIDIA_MODEL", ""),
                system_prompt_version="v1",
            )

    # Max rounds reached
    audit_steps.append({"type": "limit_reached", "reason": "max_rounds"})
    return InvestigationResult(
        status="limit_reached",
        audit_steps=audit_steps,
        rounds_used=rounds,
        retrieved_event_ids=list(retrieved_event_ids),
        retrieved_record_ids=list(retrieved_record_ids),
        model_name=model_name or os.getenv("NVIDIA_MODEL", ""),
        system_prompt_version="v1",
    )


def main():
    """CLI entry point."""
    import argparse
    from src.scenario import load_scenario, build_session

    parser = argparse.ArgumentParser(description="Run investigation on a scenario")
    parser.add_argument("--scenario", required=True, help="Path to scenario JSON")
    parser.add_argument("--out", required=True, help="Output JSON path")
    parser.add_argument("--mode", choices=["native", "json"], default=os.getenv("TOOL_MODE", "native"))
    args = parser.parse_args()

    scenario = load_scenario(args.scenario)
    session = build_session(scenario)

    question = scenario.get("question", "Investigate the events.")
    result = run_investigation(session, question, llm_mode=args.mode)

    # Save result
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(result.model_dump(mode="json"), f, indent=2, default=str)

    print(f"Status: {result.status}")
    print(f"Rounds: {result.rounds_used}")
    print(f"Tool calls in audit: {sum(1 for s in result.audit_steps if s.get('type') == 'tool_call')}")
    print(f"Saved to {args.out}")

    session.conn.close()


if __name__ == "__main__":
    main()