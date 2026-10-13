# README FIRST — 3 steps

## Step 1: Put these files in your project folder
Open PowerShell INSIDE your project folder (File Explorer -> open the folder -> click the address bar ->
type `powershell` -> Enter). Then, if the zip is in Downloads:

    Expand-Archive -Path "$HOME\Downloads\cyberimmune_project.zip" -DestinationPath . -Force
    dir

You should see: AGENTS.md, PROJECT_BRIEF.md, PROGRESS.md, SPEC.md, SUBMISSION_CHECKLIST.md, and a prompts folder.

## Step 2: Start opencode and connect Nemotron
    opencode
Connect your Nebius provider and a Nemotron model by following opencode's own documentation (I have not
verified its current setup steps). Never put your API key in a file that goes to GitHub.

## Step 3: Send this same message at the start of EVERY session
    Read PROJECT_BRIEF.md, AGENTS.md, SPEC.md and PROGRESS.md. Then do the first unfinished phase, using its file in
    the prompts folder. Do only that phase, run the tests, and stop.

When the phase is finished:
1. Run the "Done when" commands yourself and read the output.
2. Commit to GitHub (check that .env is NOT listed in `git status`).
3. Tell opencode: "Phase N is done." (it ticks the box in PROGRESS.md)
4. Close opencode and start a NEW session for the next phase.

## If something goes wrong
Paste the contents of prompts/99_debug_helper.md into opencode, or bring the exact error message to
Claude or ChatGPT. Do not skip failing tests.

## Safety
Never paste your API key into any chat. Never commit .env. Synthetic data only.
