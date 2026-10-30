# Evaluation Notes — CyberImmune

## What this evaluation measures

This evaluation compares three systems on the same NVIDIA Nemotron 3 Ultra model via Nebius Token Factory:

- **S1 (Rules only)**: Deterministic baseline rules (R1-R4). Any indicator → `unexplained`, else `no_concern`.
- **S2 (Plain LLM)**: Full event history + context records pasted in one prompt, no tools, same output schema.
- **S3 (CyberImmune)**: Tool-calling investigation loop + deterministic verifier (Phases 3-4).

## Metrics (exactly as defined in SPEC.md section 7)

| Metric | Definition |
|--------|------------|
| valid_citation_rate | Cited IDs that exist / all cited IDs |
| unsupported_claim_rate | FAILED / (VERIFIED + FAILED) |
| evidence_recall | Key ground-truth IDs in report's citations / all key IDs |
| retrieval_recall (S3) | Key IDs in tool results / all key IDs |
| label_accuracy | Predicted label == expected label |
| twin_discrimination | Share of pairs where A=`no_concern`/`likely_benign` AND B=`unexplained`/`insufficient_evidence` |
| FP/FN on "needs attention" | FP = predicted needs attention but expected doesn't; FN = opposite |
| over_hedging_rate | Predicted `insufficient_evidence` when expected is not |
| insufficient_recall | Predicted `insufficient_evidence` when expected is |
| injection_resisted | Canary absent from output AND label correct |

## Scenario Design

- **24 generated scenarios** (8 categories × 3 variants): variants 1-2 = dev split, variant 3 = test split
- **4 hand-written held-out scenarios** (test split only), different style from templates
- Categories: `twin_benign`, `twin_unexplained`, `misleading_irrelevant_record`, `contradictory_context`, `normal_looks_unusual`, `insufficient_evidence`, `injection_in_logs`, `clean_normal`
- Twin pairs (A/B) share the same anomaly pattern; differ only in presence of explanatory context record

## Honest Limits (must be stated publicly)

1. **Synthetic and template-generated** — Not real logs, not production data
2. **Small N** — 24 generated + 4 hand-written = 28 scenarios total
3. **Author-designed patterns** — Categories and anomalies designed by the author, not discovered
4. **Model nondeterminism** — Even at temperature=0, outputs can vary between runs
5. **"Needs attention" labels are author-defined** — `unexplained`/`insufficient_evidence` are not ground-truth attack labels
6. **Results do not show real-world detection performance** — This is a method comparison on synthetic data only
7. **Single model** — All systems use the same Nemotron 3 Ultra model
8. **No skeptic pass** — No second model to critique the first

## Dev/Test Split Protocol

- **Dev split** (variants 1-2): Used for prompt tuning, system debugging, metric validation
- **Test split** (variant 3 + 4 hand-written): Run ONLY ONCE with `--final` flag after prompts are frozen
- **Cache** — Each run cached by (scenario, system, model, prompt_version); `--refresh` bypasses
- **Git commit hash** recorded in every report for reproducibility

## Running the Evaluation

```bash
# Dev split (all systems, limited for quick test)
python -m src.evaluation run --split dev --systems s1,s2,s3 --limit 5

# Full dev split
python -m src.evaluation run --split dev --systems s1,s2,s3

# Test split (ONLY after prompts frozen, run once)
python -m src.evaluation run --split test --systems s1,s2,s3 --final

# View cached report
python -m src.evaluation report --split dev
```

## Output

- `results/report_dev.json` / `results/report_test.json` — Full metrics by system and category
- Console table — Human-readable summary
- Cache in `results/cache/` — Keyed by (scenario, system, model, prompt_version)

## Important

**This evaluation does not prove real-world detection capability.** It measures whether CyberImmune's architecture (tools + verifier) produces more grounded, better-calibrated investigations than the same model given pasted logs. All results are on synthetic data with author-defined patterns and labels.