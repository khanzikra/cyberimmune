# Phase 9 — Demo video script (under 3 minutes)

Read first: README.md and the real results. This phase writes a script and shot list only. No code.

## Rules
Show the working app, not slides. Do not exaggerate. Do not say it "detects attacks" or "eliminates
hallucination". Total length target: 2:30 (hard limit under 3:00). Every number spoken must exist in the
results files.

## Produce
A table with columns: time, what is on screen, narration (written to be read aloud in simple English).
Suggested structure:
1. 0:00-0:20 Problem: AI security assistants sound confident; their claims may not match the logs.
2. 0:20-0:40 Idea: the model investigates with read-only tools; Python checks every factual claim.
3. 0:40-1:10 Twin A: same unusual login, an IT ticket exists. Show tool calls, claims, green badges.
4. 1:10-1:40 Twin B: same activity, no record. Different conclusion label; missing evidence listed.
5. 1:40-2:00 A made-up claim from the plain-LLM baseline flagged red by the verifier.
6. 2:00-2:25 Evaluation Lab: the three systems side by side, with honest numbers and limits.
7. 2:25-2:45 Where Nebius Token Factory and the NVIDIA Nemotron model are used (show llm_client.py and the
   architecture diagram). Close with the honest contribution: auditable claims, not perfect security.
Also give: a recording checklist (resolution, hide the terminal env vars, no key on screen, close
notifications), and a list of backup shots in case a live run fails (use cached results).

## Stop rules
Do not write code. Do not add claims beyond the real results.
