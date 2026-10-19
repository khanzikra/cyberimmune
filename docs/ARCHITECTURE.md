# Architecture Documentation

## Data Flow Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        CYBERIMMUNE ARCHITECTURE                               │
└─────────────────────────────────────────────────────────────────────────────┘

1. SYNTHETIC DATA GENERATION (Phase 1)
   ┌──────────────┐    seed=42    ┌──────────────┐    ┌──────────────────┐
   │ Python RNG   │ ────────────► │ generate_    │ ──► │ events table     │
   │ (determinist)│               │ history()    │     │ context_records  │
   └──────────────┘               └──────────────┘     │ (SQLite)         │
                                                        └──────────────────┘
                                                          │
                                                          ▼
2. BASELINE COMPUTATION (Phase 1)
   ┌──────────────┐    cutoff     ┌──────────────┐    ┌──────────────────┐
   │ Events before│ ────────────► │ compute_     │ ──► │ login_hour_hist  │
   │ cutoff       │               │ baseline()   │     │ known_devices    │
   └──────────────┘               └──────────────┘     │ top_resources    │
                                                        │ avg_events/day   │
                                                        └──────────────────┘
                                                          │
                                                          ▼
3. INDICATOR DETECTION (Phase 1)
   ┌──────────────┐    focus win  ┌──────────────┐    ┌──────────────────┐
   │ Events in    │ ────────────► │ find_        │ ──► │ R1 unusual_hour  │
   │ window       │               │ indicators() │     │ R2 new_device    │
   └──────────────┘               └──────────────┘     │ R3 rare_resource │
                                                        │ R4 failure_burst │
                                                        └──────────────────┘
                                                          │
                                                          ▼
4. SCENARIO BUILDING (Phase 5)
   ┌──────────────┐    inject     ┌──────────────┐    ┌──────────────────┐
   │ Base history │ ────────────► │ build_       │ ──► │ In-memory SQLite │
   │ + injected   │               │ session()    │     │ (read-only)      │
   │ + context    │               └──────────────┘     └──────────────────┘
   └──────────────┘
                                                          │
                                                          ▼
5. INVESTIGATION LOOP (Phase 3)
   ┌──────────────┐    Q + Tools  ┌──────────────┐
   │ Question +   │ ────────────► │ LLM          │
   │ System Prompt│               │ (Nemotron    │
   └──────────────┘               │ via Nebius)  │
        ▲                         └──────┬───────┘
        │                                │ tool calls
        │                                ▼
        │                         ┌──────────────┐
        │                         │ TOOL DISPATCH│
        │                         │ validate +   │
        │                         │ execute      │
        │                         └──────┬───────┘
        │                                │ results
        └────────────────────────────────┘
        │
        ▼
   ┌──────────────┐
   │ Final JSON   │
   │ Investigation│
   └──────┬───────┘
          │
          ▼
6. EVIDENCE VERIFIER (Phase 4)
   ┌──────────────┐    claims     ┌──────────────┐
   │ Investigation│ ────────────► │ verify_      │
   │ + DB + cutoff│               │ investigation│
   └──────────────┘               └──────┬───────┘
                                         │
              ┌──────────────────────────┼──────────────────────────┐
              ▼                          ▼                          ▼
       ┌──────────────┐           ┌──────────────┐           ┌──────────────┐
       │ CITATION     │           │ FIELD        │           │ RELATIONSHIP │
       │ event exists │           │ value match  │           │ ORDER,       │
       │ record exists│           │ ts/device/   │           │ DEVICE_FAM,  │
       └──────────────┘           │ resource...  │           │ CONTEXT      │
                                  └──────────────┘           └──────────────┘
              │                          │                          │
              ▼                          ▼                          ▼
       ┌──────────────────────────────────────────────────────────────────┐
       │ VERIFICATION REPORT                                              │
       │ Per claim: claim_id, status (VERIFIED/FAILED/NOT_CHECKABLE),    │
       │ checks_run, explanation, provenance_ok, original_claim          │
       │ Summary: valid_citation_rate, unsupported_claim_rate            │
       └──────────────────────────────────────────────────────────────────┘

7. EVALUATION (Phase 5)
   ┌──────────────┐    scenarios  ┌──────────────┐    ┌──────────────┐
   │ Scenarios    │ ────────────► │ run_system() │ ──► │ S1: Rules    │
   │ (dev/test)   │               │ + verify()   │     │ S2: Plain    │
   └──────────────┘               └──────────────┘     │ S3: Full     │
          │                                              └──────┬───────┘
          │                                                     │
          ▼                                                     ▼
   ┌──────────────┐                                   ┌──────────────┐
   │ METRICS      │                                   │ CACHE        │
   │ label_acc    │                                   │ key: scen,   │
   │ evidence_rcl │                                   │ sys, model,  │
   │ retrieval_rcl│                                   │ prompt_ver   │
   │ twin_discrim │                                   └──────────────┘
   │ injection_rst│
   └──────────────┘

8. STREAMLIT UI (Phase 6/7)
   ┌──────────────┐    cached     ┌──────────────┐
   │ results/     │ ────────────► │ 3 Screens    │
   │ final/       │               │ 1. Timeline  │
   │ (DEMO MODE)  │               │ 2. Invest    │
   └──────────────┘               │ 3. Eval Lab  │
                                  └──────────────┘
```

## Tool-Calling Loop (Simple Words)

1. **Start**: We have a question (e.g., "Investigate user_01's unusual login") and a read-only database connection with a fixed baseline cutoff.

2. **Round 1**: Send the question + system prompt + 3 tool schemas to the LLM.
   - The LLM can call: `query_events`, `get_baseline`, `get_context`

3. **Tool Execution**: Python validates every call:
   - User ID must match `^user_\d{2}$`
   - Event types from allowlist only
   - Timestamps ISO 8601, range ≤ 45 days
   - Limits capped (50 events, 20 context)
   - Parameterized SQL only, `PRAGMA query_only=ON`

4. **Results Returned**: Tool results go back as "tool" messages (truncated to 6000 chars).
   - Untrusted text fields in `details_untrusted` / `summary_untrusted`

5. **Repeat**: Up to 6 rounds, max 10 total tool calls.

6. **Final Answer**: When LLM stops calling tools, ask for Investigation JSON.
   - Validate with Pydantic (claim IDs sequential, structured fields match claim_type)
   - If invalid: one retry with error message
   - If still invalid: status = "validation_error"

7. **Output**: `InvestigationResult` with investigation, status, audit_steps, rounds_used, retrieved IDs.

## Verification Checks (Simple Words)

For each claim in the investigation:

| Claim Type | Checks Run |
|------------|------------|
| EVENT_EXISTS | 1. Citation: event_id exists in DB |
| FIELD_VALUE | 1. Citation + 2. Field equals stated value (timestamps normalized) |
| ORDER | 1. Both exist + 2. first.ts < second.ts (strict) |
| DEVICE_FAMILIARITY | 1. Citation + 2. Device in baseline for user == claimed familiar |
| CONTEXT_EXISTS | 1. Citation + 2. Optional user_id/record_type match |
| INTERPRETATION / HYPOTHESIS / MISSING_EVIDENCE | NOT_CHECKABLE — "Interpretive validity is not machine-checkable" |

**Provenance**: Every cited ID must have been in the tool results (provenance_ok). A claim can be VERIFIED but have provenance_ok=False (UI shows warning).

**Failed claims are never deleted** — they stay in the report with the failure reason.

## DEMO MODE vs LIVE MODE

| Aspect | DEMO MODE (default) | LIVE MODE (ENABLE_LIVE=1) |
|--------|---------------------|---------------------------|
| Data source | `results/final/` (cached) | `results/` + live LLM |
| API keys | None needed | Nebius credentials from env |
| Cost | $0 (free) | Credits per call |
| Rate limits | None | 3 runs/session, daily cap |
| Screens | All 3 work | All 3 + "Run Live" button |

## Key Design Principles

1. **No secrets in UI** — `os.getenv` / `st.secrets` only in backend, never in frontend
2. **Deterministic verification** — Python checks, no second LLM
3. **Read-only tools** — `PRAGMA query_only=ON`, validated params, parameterized SQL
4. **Untrusted text isolated** — truncated, `details_untrusted`, never `unsafe_allow_html`
5. **Failed claims visible** — never hidden, reason shown
6. **Interpretations labeled** — NOT_CHECKABLE with clear explanation
7. **Cache everything** — evaluation results keyed by (scenario, system, model, prompt_version)
7. **Test split protected** — `--final` flag required, run once