# Phase 6 — Streamlit interface (3 screens)

Read first: AGENTS.md, SPEC.md. Do ONLY this phase, then stop. Add streamlit and plotly to requirements.txt.

## Goal
A clean, professional console where a judge can see the difference between an AI-generated claim and a claim
that passed deterministic verification. Transparency over decoration.

## Tasks
1. app.py with a sidebar to pick the screen, and a scenario selector. Data comes from saved results in
   results/ (investigations, verification reports, evaluation report) and data/scenarios/. The app must work
   fully WITHOUT any API key (demo mode reads cached results).
2. Screen 1 "Timeline": Plotly timeline of the focus user's events (x = time, y = event type, colour =
   normal vs flagged by a baseline rule), related events connected, and an evidence panel that shows the full
   source record (event_id, ts, device, resource, outcome) for the selected event, plus which rules fired.
3. Screen 2 "Investigation": the question; tool calls and result summaries (audit steps); the conclusion
   label; each claim with a coloured badge: green VERIFIED, red FAILED (with the reason), grey NOT_CHECKABLE
   ("model's interpretation"); a provenance warning if a cited ID was never retrieved; supporting and
   contradicting links; hypotheses; missing evidence; next steps for a human (never automatic actions).
   Add a plain-language box: "What the verifier proves / does not prove".
4. Screen 3 "Evaluation Lab": pick a scenario, show expected ground truth next to S1, S2, S3 results; counts of
   valid/invalid citations; the metric table from results/report_*.json; the limits paragraph.
5. Security: NEVER render log or ticket text with unsafe_allow_html. Show untrusted text via st.text/st.code
   or escape it. Badges may use fixed HTML you wrote, never model or log text.
6. Style: .streamlit/config.toml with a dark theme and one accent colour; consistent spacing; no
   animations; wide layout.
7. tests/test_app_smoke.py: importing app helper functions works; helper that formats badges escapes HTML in
   a malicious claim text.

## Done when
- `streamlit run app.py` starts and all three screens render using cached results.
- The USER can follow one full scenario (twin A vs twin B) without help.

## Stop rules
No new features, no extra pages, no live LLM calls from the UI yet (Phase 7).
