# Phase 5 — Scenarios and the benign-twin evaluation

Read first: AGENTS.md, SPEC.md section 7 (all of it). Do ONLY this phase, then stop.

## Goal
A reproducible benchmark comparing three systems on the same model, with exactly defined metrics, a dev/test
split, and honest reporting.

## Tasks
1. src/scenario_gen.py: template functions for the 8 categories in SPEC.md section 7, 3 variants each
   (seeded; each variant picks different users, devices, resources, hours, dates, ticket wording from
   pools; keep some pool values for the test split only). Writes data/scenarios/<scenario_id>.json with
   ground truth, key IDs, split, pair_id/pair_role. The twin pair A/B must share the same anomaly pattern
   and differ only in the presence of the matching context record. The injection scenario puts a harmless
   canary phrase and an "ignore previous instructions" style line in an event details field (a text that
   asks the model to output the canary).
2. data/scenarios_handwritten/: write 4 held-out scenarios by hand in a DIFFERENT style from the
   templates (different structure of events), split "test". Ask the user to review them.
3. src/evaluation.py
   - run_system(system, scenario, llm): S1 rules only; S2 plain LLM (that user's full history + context
     records pasted in one prompt, same output schema, no tools); S3 the Phase 3 investigator.
   - Verify S2 and S3 outputs with the Phase 4 verifier.
   - Metrics exactly as in SPEC.md section 7 (valid_citation_rate, unsupported_claim_rate, evidence_recall,
     retrieval_recall, label_accuracy, twin_discrimination, FP/FN, over_hedging_rate, insufficient_recall,
     injection_resisted), per system and per category.
   - Cache each run in results/cache/ keyed by (scenario_id, system, model, prompt_version); `--refresh`
     bypasses the cache.
   - CLI: `python -m src.evaluation run --split dev --systems s1,s2,s3 --limit 5`
          `python -m src.evaluation report --split dev` (prints a table; also writes results/report_<split>.json)
   - The test split runs ONLY with `--final`; without it the code refuses. Record git commit hash,
     model name and prompt version in the report file.
   - S2 and S3 use the same model, temperature and token limits. Failures (invalid JSON, limit reached)
     are counted and reported, never dropped.
4. tests/test_evaluation_metrics.py: tiny hand-computed examples for every metric, a test that the test
   split refuses without --final, and a test that ground truth never appears in the S2 prompt or the tool
   session.
5. Add a short "Evaluation limits" paragraph to EVALUATION_NOTES.md (synthetic, template-based, small N,
   author-defined labels, nondeterminism, no real-world claim).

## Done when
- `python -m pytest -q` passes.
- `python -m src.evaluation run --split dev --systems s1 ` works with no credits (rules only).
- The USER runs `--limit 3` for S2 and S3 first, then the full dev split, and shares report_dev.json.
- Prompts are tuned on dev only. After the user freezes prompts, the test split is run ONCE with --final.

## Stop rules
Do not tune on the test split. Do not drop failed runs. Do not add a skeptic pass or extra models.
