# Phase 8 — Documentation

Read first: AGENTS.md, SPEC.md, EVALUATION_NOTES.md, the real results files. Do ONLY this phase, then stop.

## Rule
Every number in the docs must come from a real results file. Do not invent or round up results. If a result
is unimpressive, report it honestly.

## Tasks
1. README.md: title and tagline "AI can make the claim. Evidence must prove it."; the problem; what the
   system does; an architecture diagram (Mermaid or ASCII); a table "Where Nebius and NVIDIA are used"
   (file name + what it does: llm_client.py calls Nemotron through Nebius Token Factory; investigator.py
   tool-calling loop; S2/S3 evaluation runs); setup and run instructions for PowerShell; how to run tests;
   how to run the evaluation; the results table (S1 vs S2 vs S3); what the verifier proves and does not prove;
   limitations; safety notes (synthetic data, read-only tools, untrusted logs, no auto-actions); licence.
2. "Related work" section: short, careful comparison with AI SOC agents, UEBA/SIEM and timeline tools.
   Do not claim novelty beyond "the combination of a deterministic claim verifier with a benign-twin
   evaluation, as an open-source, reproducible prototype". Mark anything you are unsure of as "to be checked".
3. Check LICENSE exists and is an OSI-approved licence (MIT).
4. Finish FEEDBACK.md from the notes taken during development (what was confusing, what failed, what worked,
   suggestions). Keep it factual.
5. docs/ARCHITECTURE.md with the data flow and the tool-calling loop in simple words.

## Done when
- A person who has never seen the project can set it up from the README alone (the USER tests this on a
  fresh clone).

## Stop rules
No code changes except fixing documented commands that do not work.
