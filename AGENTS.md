# AGENTS.md — rules for the coding assistant (read this first, every session)

## Who you are helping
A beginner Python student building a hackathon project called CyberImmune.
Explain what you do in simple language. Prefer simple, readable code over clever code.

## Working style
- Do ONE phase at a time (the prompt names it). Do not start the next phase.
- Make small changes. After each file, run the relevant test or command and show the REAL output.
- Never say something works unless you ran it. If you could not run it, say "not run".
- If a command fails: show the exact error, name the most likely cause, try a fix. After 3 failed
  attempts at the same problem, STOP and ask the user.
- Ask before installing any library that is not in the allowed list.
- Read SPEC.md before writing code. SPEC.md is the single source of truth. If a prompt and SPEC.md
  disagree, stop and ask.

## Environment
- Windows + PowerShell. Use PowerShell syntax. Chain commands with `;` (not `&&`).
- Run Python through the virtual environment directly: `venv\Scripts\python.exe`
  (so no activation is needed). Wherever a prompt says `python`, use `venv\Scripts\python.exe`.
  If the venv folder does not exist yet, create it: `python -m venv venv`.
- Allowed Python libraries: openai, python-dotenv, pydantic, pandas, streamlit, plotly, pytest.
- Run tests with: venv\Scripts\python.exe -m pytest -q

## Progress tracking
- Read PROGRESS.md at the start of every session. Work on the FIRST phase not marked done.
- Do NOT mark a phase done yourself. When the user says "phase N is done", update PROGRESS.md
  (tick the box and add one line on what was verified and any known problems).

## Secrets (critical)
- NEVER open, read, print, log, or commit the .env file. Never ask the user to paste a key into chat.
- Read config only with os.getenv() after load_dotenv(). .env.example holds EMPTY placeholders only.
- Before every commit run `git status` and confirm .env is NOT listed.
- Never print API clients, request headers, or environment variables.

## Security rules for the product
- Model tools are READ-ONLY. No free-form SQL from the model, no shell, no file access,
  no network except the Nebius API call itself.
- SQL must be parameterized. Every tool argument is validated (allowlist / regex / caps).
- Log text (event details, ticket summaries) is UNTRUSTED data. Give it to the model labelled as data,
  never execute it, never render it as HTML in the UI.
- Ground-truth labels in scenario files must never reach the model or be reachable from tools.
- Model output must be validated (pydantic) before it is used.

## Honesty rules for the product
- An anomaly is not an attack. Never output words like "compromised" or "attack confirmed".
- The verifier proves ONLY: citation exists, field matches, event order, device familiarity per baseline,
  context record exists. It does NOT prove interpretations. Say so in code comments and the UI.
- Do not invent Nebius or NVIDIA API parameters. Use only what test_a.py / test_b.py showed working,
  or what the user confirms from the official Nebius docs.
- Never claim synthetic-data results prove real-world detection performance.

## Project map
See PROJECT_BRIEF.md (the whole idea) and SPEC.md (technical details). Prompts for each phase are in the prompts/ folder.
