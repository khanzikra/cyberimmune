# Phase 1 — Synthetic data and baseline rules

Read first: AGENTS.md, SPEC.md sections 2 and 3. Do ONLY this phase, then stop.

## Goal
A deterministic synthetic dataset in SQLite and four explainable baseline rules with tests.

## Tasks
1. src/database.py
   - create_schema(conn): tables events and context_records exactly as in SPEC.md section 2, with CHECK
     constraints for the allowlists.
   - helpers: connect(path), insert_events(conn, rows), insert_context(conn, rows).
2. src/data_generator.py
   - generate_history(seed=42) -> list of event dicts: 10 users x 30 days following SPEC.md section 2.
     Use Python's random.Random(seed) only (no global random). Same seed => identical output.
   - CLI: `python -m src.data_generator --db data/history.db` writes the DB.
   - Include 2 users with legit night-time patterns. Details text must be short, plain, and harmless.
3. src/baseline.py
   - compute_baseline(conn, user_id, cutoff) -> dict (fields listed under get_baseline in SPEC.md).
   - find_indicators(conn, user_id, cutoff, window_start, window_end) -> list of
     {rule, event_id, detail} for rules R1-R4 in SPEC.md section 3.
4. tests/test_data.py and tests/test_baseline.py:
   - same seed gives identical events; different seed differs
   - schema rejects an invalid event_type
   - a planted event (new device + 03:00 UTC + never-used resource) triggers R1, R2, R3
   - a normal event on a usual device in usual hours triggers nothing
   - R4 triggers for 3 failed logins in 10 minutes and not for 3 spread over an hour
   - baseline_sufficient is False when fewer than 20 baseline logins
5. A tiny script scripts/check_flag_rate.py: use days 1-20 as baseline and report the share of normal
   events on days 21-30 that the rules flag, per rule. PRINT the numbers; do not tune them to look good.

## Done when
- `python -m pytest -q` passes.
- `python -m src.data_generator --db data/history.db` creates the DB; show row counts per table and user.
- The flag-rate numbers are printed and shown to the user.

## Stop rules
No LLM calls in this phase. No tools, no Streamlit. Stop after the tests pass and report the flag rates.
