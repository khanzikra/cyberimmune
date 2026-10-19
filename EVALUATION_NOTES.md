# Evaluation Limits and Caveats

## What this evaluation measures
This benchmark compares three systems on **synthetic, template-generated scenarios** with **small N (24 dev + 4 test scenarios)** using **author-defined ground truth labels**. It measures internal consistency and evidence grounding, not real-world detection performance.

## Key limitations

1. **Synthetic data only**: Events and context records are generated from templates with seeded randomness. Patterns are author-designed, not drawn from real security incidents.

2. **Template-based scenarios**: The 8 categories cover specific anomaly patterns (twin benign/unexplained, misleading records, contradictory context, weak indicators, insufficient baseline, injection attempts, clean baseline). Real attacks may not fit these categories.

3. **Small N**: 24 dev scenarios (3 variants × 8 categories) + 4 hand-written test scenarios. Statistical significance is limited.

4. **Author-defined labels**: Ground truth labels (no_concern, likely_benign, unexplained, insufficient_evidence) are assigned by the scenario author. Different analysts might disagree on some edge cases.

5. **Model nondeterminism**: Even at temperature=0, LLM outputs can vary between runs. Results are cached but not replicated.

6. **No real-world claim**: High scores on this benchmark do **not** imply the system would detect real attacks in production. The benchmark tests evidence grounding and calibration on known patterns.

7. **Single model**: All systems use the same model (Nemotron 3 Ultra via Nebius). Results may not generalize to other models.

8. **Binary evaluation of claims**: The verifier checks factual claims only. It cannot assess whether the model's interpretations or hypotheses are reasonable.

9. **Dev/test split discipline**: Prompts are tuned on dev only. Test split is run **once** with `--final` flag. No iterative tuning on test.

10. **Failure handling**: Failed runs (invalid JSON, limit reached) are counted and reported, not dropped. This penalizes unstable systems.

## What "valid_citation_rate" means here
The fraction of cited event/record IDs that actually exist in the database. Does not measure whether the *right* IDs were cited.

## What "unsupported_claim_rate" means here
FAILED / (VERIFIED + FAILED) for checkable claims. Does not measure whether FAILED claims are important or trivial.

## What "evidence_recall" means here
The fraction of author-designated "key IDs" that appear in the report's citations. Key IDs are chosen by the scenario author.

## What "retrieval_recall" means here (S3 only)
The fraction of key IDs that appeared in tool results. Measures whether the investigator *found* the evidence, not whether it used it.

## What "injection_resisted" means here
Whether the model avoided outputting a canary string planted in event details. Tests basic instruction-following hygiene, not full prompt injection robustness.

## What "twin_discrimination" means here
Whether the system correctly flips its conclusion between twin scenarios that share the same anomaly but differ only in the presence of an explaining context record. This is the core "benign twin" test.

## Honest reporting requirement
All reports must include: model name, prompt version, git commit, timestamp, split, and the above caveats. No cherry-picking of metrics or scenarios.