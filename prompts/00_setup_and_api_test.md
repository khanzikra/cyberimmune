# Phase 0 — Project setup and Nebius API test

Read first: AGENTS.md, SPEC.md (skim). Do ONLY this phase, then stop.

## Goal
Working project skeleton and proof that Python can call a Nemotron model on Nebius Token Factory,
including a tool-call test.

## Facts you must NOT guess
The API key, base URL and model name come from the user's Nebius console/docs. Use placeholders.
Never open .env.

## Tasks (in order, explain each in simple language)
0. Check `git status`. If this folder is not a git repository, tell me and explain simply how to connect it
   to my GitHub repo (git init, git remote add origin <url>); wait for me to do it. If the venv folder
   does not exist, create it with `python -m venv venv`. Do not create a LICENSE or .gitignore if they
   already exist; only add missing lines.
1. Create folders: src/, tests/, data/, results/. Add empty src/__init__.py and tests/__init__.py.
2. Create pytest.ini containing:
   [pytest]
   pythonpath = .
3. Create requirements.txt: openai, python-dotenv, pydantic, pandas, pytest
   (streamlit and plotly are added later in Phase 6).
4. Create .env.example with EMPTY values for: NEBIUS_API_KEY, NEBIUS_BASE_URL, NEBIUS_MODEL, TOOL_MODE
   (TOOL_MODE will be "native" or "json"; leave empty).
5. Check .gitignore contains these lines; show me any that are missing and add them:
   .env, venv/, *.db, __pycache__/, .pytest_cache/
6. Create test_a.py: load .env, build an OpenAI client from the three variables, send one chat message
   ("Say hello in one short sentence."), print the reply. If a variable is missing, print which one and exit
   cleanly. Never print the key. Handle API errors with a readable message.
7. Create test_b.py: same client; send "Show me the logins for user_07." with ONE fake tool query_events
   (parameter user_id: string, required). Print whether the model returned a tool call; if so print its
   name and parsed arguments (parse JSON safely). If there is no tool call, say so plainly.
8. Create FEEDBACK.md with headings: What was confusing / What was slow or failed / What worked well /
   Suggestions for Nebius and NVIDIA. (The hackathon requires feedback; we fill it in as we go.)
9. Create a README.md skeleton: title, one-line description, setup steps, "How Nemotron and Nebius Token
   Factory are used" (TODO), "Evaluation" (TODO), "Limitations" (TODO).
10. Give me the exact PowerShell commands to run, in order:
    pip install -r requirements.txt ; python test_a.py ; python test_b.py ; git status ; git add ; git commit ; git push

## Done when (the USER runs these and reports the output)
- test_a.py prints a sentence.
- test_b.py prints a tool call for query_events with user_07, OR clearly says no tool call came back.
- `git status` does NOT list .env.

## Stop rules
Stop after task 10. Do not create databases, Streamlit pages or agents.
If test_b returns no tool call, do NOT work around it yet; tell the user and wait.
