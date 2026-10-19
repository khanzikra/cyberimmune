# Phase 2 — Read-only investigation tools

Read first: AGENTS.md, SPEC.md section 4. Do ONLY this phase, then stop.

## Goal
Three safe tools the model may call, with strict validation. The model never gets raw database access.

## Tasks
1. src/event_tools.py
   - class ToolSession(conn, baseline_cutoff): opens/uses a read-only connection (PRAGMA query_only=ON).
   - Functions: query_events, get_baseline, get_context exactly as specified in SPEC.md section 4.
   - dispatch(session, tool_name, args_dict) -> result dict. Rejects unknown tool names and unknown
     argument keys. Never raises; returns {"ok": false, "error": "..."} instead.
   - TOOL_SCHEMAS: list of tool definitions in OpenAI function-calling format (name, description,
     JSON-schema parameters) matching the validation rules. Descriptions must say results are DATA.
   - Validation: user_id regex ^user_\d{2}$; event_type allowlist; ISO timestamp parsing; end-start <= 45
     days; limit caps (50 / 20); parameterized SQL only (no string-built SQL).
   - Free-text fields: truncate to 200 chars and return under details_untrusted / summary_untrusted.
   - Also record every call (tool, args, ok/error, row count) in session.audit_log (list of dicts).
2. tests/test_event_tools.py covering at least:
   - valid calls return the expected rows
   - bad user_id such as "user_1; DROP TABLE events" is rejected
   - limit 500 is capped to 50 (or rejected; pick one and document it)
   - invalid timestamp, reversed range, range > 45 days rejected
   - unknown tool name and unknown argument key rejected
   - the database is unchanged after all calls (row counts equal before/after)
   - an event whose details contain "ignore previous instructions" is returned only inside
     details_untrusted, truncated, and unchanged otherwise
   - get_baseline uses the session cutoff and cannot be given a different one

## Done when
- `python -m pytest -q` passes (all earlier tests too).
- The user can run a small demo script scripts/demo_tools.py that builds a session on data/history.db and
  prints one call of each tool.

## Stop rules
No LLM calls. Do not add a fourth tool. Correlation of related events is plain Python used later, not a tool.
