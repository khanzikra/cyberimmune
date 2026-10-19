# Phase 10 — Final checks before submitting

Read first: AGENTS.md, ../SUBMISSION_CHECKLIST.md. Do ONLY this phase.

## Tasks
1. Run `python -m pytest -q`; report the real result.
2. Secret scan: search the whole repo AND git history for key-like strings and the name of the env vars with
   values (PowerShell: Select-String -Path (Get-ChildItem -Recurse -File | Where-Object {$_.FullName -notmatch 'venv|\.git'}) -Pattern 'NEBIUS_API_KEY\s*=\s*\S+').
   Also run `git log -p | Select-String -Pattern 'api_key|NEBIUS_API_KEY=.+'`. Report findings; if anything
   real is found, STOP and tell the user to rotate the key.
3. Confirm .env is ignored and was never committed (`git log --all -- .env`).
4. Fresh-clone test: clone the repo into a new folder, create a venv, install, run tests, start the app in
   demo mode. Report what broke.
5. Check each item in SUBMISSION_CHECKLIST.md and mark it done / not done with evidence (file path or URL).
6. Verify the README numbers match results/final files.
7. List remaining risks honestly.

## Stop rules
Do not add features. Fix only what blocks submission.
