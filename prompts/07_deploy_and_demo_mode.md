# Phase 7 — Hosted demo that cannot burn credits

Read first: AGENTS.md. Do ONLY this phase, then stop.

## Facts from the rules to respect
A hosted demo URL is required; judges must be able to open it free; it must stay available until judging
ends (Dec 15). Nebius deployment is encouraged but not required.

## Tasks
1. DEMO_MODE (default true): the app reads cached results from results/final/ (commit these files; they are
   synthetic and key-free). Add a script to copy the final dev/test results and example investigations there.
2. Optional "Run live" button that is OFF unless an env var ENABLE_LIVE=1 is set. When on: max 3 runs per
   session, a global daily cap read from an env var, and a clear message when exhausted. It must never
   expose keys; read them with os.getenv / st.secrets only.
3. No login for judges. No personal data anywhere.
4. Pin versions in requirements.txt; make sure the app starts from a clean clone with only cached results.
5. DEPLOY.md: step-by-step manual instructions for deploying on Streamlit Community Cloud (the user does
   this by hand): connect the GitHub repo, main file app.py, add secrets only if ENABLE_LIVE is used. Include
   how to test the URL in a private browser window. Mention the optional Nebius deployment but do not require it.
6. Add a startup self-check that prints (to the log, no secrets) whether it is in demo mode.

## Done when
- A fresh clone + `pip install -r requirements.txt` + `streamlit run app.py` works without a .env file.
- The USER deploys following DEPLOY.md and the URL opens in a private window.

## Stop rules
Do not build new analysis features. Do not commit secrets or the .env file.
