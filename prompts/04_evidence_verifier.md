# Phase 4 — Deterministic evidence verifier (the centerpiece)

Read first: AGENTS.md, SPEC.md sections 5 and 6. Do ONLY this phase, then stop.

## Goal
Python independently checks every checkable claim against the database and the baseline, keeps a full audit
trail, and never pretends to prove interpretations.

## Tasks
1. src/evidence_verifier.py
   - verify_investigation(investigation, conn, baseline_cutoff, retrieved_event_ids=None,
     retrieved_record_ids=None) -> VerificationReport
   - Per claim return: claim_id, status (VERIFIED | FAILED | NOT_CHECKABLE), checks_run (list of
     {level: citation|field|relationship, passed, detail}), explanation (plain English), and
     provenance_ok (True/False/None). The original claim text is copied unchanged into the report.
   - Implement exactly these checks (SPEC.md section 6):
     EVENT_EXISTS: the event_id exists.
     FIELD_VALUE: exists AND the stated field equals the stated value (normalize timestamps).
     ORDER: both exist AND first.ts < second.ts (strictly).
     DEVICE_FAMILIARITY: device seen for that user before the cutoff == claimed `familiar`.
     CONTEXT_EXISTS: record exists AND optional user_id / record_type match.
     Also check that every ID listed in cited_event_ids / cited_record_ids exists (citation level), and
     that a claim about a user cites events that belong to that user where a user is stated.
   - INTERPRETATION, HYPOTHESIS, MISSING_EVIDENCE => NOT_CHECKABLE with the explanation
     "Interpretive validity is not machine-checkable; shown as the model's interpretation."
   - Factual claim with missing/malformed structured fields => FAILED (reason: malformed).
   - Provenance: provenance_ok = every cited ID was in the retrieved sets (None if sets not given).
     A claim can be VERIFIED yet have provenance_ok False; the UI will show a warning.
   - VerificationReport.summary: counts per status and the rates defined in SPEC.md section 7
     (valid_citation_rate, unsupported_claim_rate).
   - NEVER delete or edit failed claims. The report must contain every claim.
2. tests/test_verifier.py with a table of claims (use a small in-memory DB):
   TRUE claims that must be VERIFIED: one per factual type.
   PLANTED FALSE claims that must be FAILED (at least 10): nonexistent event ID; right event wrong user;
   wrong timestamp; wrong device; wrong resource; ORDER reversed; DEVICE_FAMILIARITY wrong; fake context
   record; context record that belongs to another user; malformed structured field.
   Plus: interpretations are NOT_CHECKABLE; failed claims remain in the report; summary rates are correct
   on a hand-computed example; provenance warning appears when a cited event was never retrieved.
3. scripts/verify_result.py: loads a results JSON from Phase 3 + rebuilds its scenario DB, prints a readable
   table of claim, status, reason.

## Done when
- `python -m pytest -q` passes, including 100% of planted false claims caught.
- The USER runs scripts/verify_result.py on results/demo.json and sees statuses and reasons.

## Stop rules
Do not add an LLM judge to the verifier. Do not rewrite or "fix" model claims. No UI yet.
