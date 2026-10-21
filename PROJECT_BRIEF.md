# CyberImmune — the whole project, start to end

Tagline: "AI can make the claim. Evidence must prove it."

## 1. What this is
A hackathon project for the Nebius x NVIDIA Global AI Hackathon 2026 (track: Best Apps & Agents).
It is an open-source security investigation app. An NVIDIA Nemotron model, called through Nebius Token
Factory, investigates SYNTHETIC security events. Plain Python then checks every factual claim the model makes.

## 2. The problem
AI security assistants write convincing explanations of suspicious activity. But their claims may not match
the logs, and they often ignore harmless explanations (for example, an approved laptop replacement).

## 3. The idea in simple words
1. We create fake (synthetic) company logs: logins and resource access for 10 users over 30 days, plus
   "context records" such as IT tickets and approved-device records.
2. Simple rules mark unusual things: login at an odd hour, a new device, a rarely used resource, several
   failed logins in a row. An unusual event is NOT proof of an attack. It is just an observation.
3. The AI investigates by asking for information through three safe, read-only tools:
   - query_events: look up events
   - get_baseline: see what is normal for a user
   - get_context: see IT tickets / approved devices
   Python checks every request. The AI never touches the database directly.
4. The AI writes a structured report: claims (with event IDs), competing explanations, missing evidence,
   next steps for a human, and one of four labels:
   no_concern / likely_benign / unexplained / insufficient_evidence.
   It never says "compromised".
5. A verifier (plain Python, no AI) checks the claims: does the event exist, is the time/device/user right,
   did event A really happen before event B, was the device really unfamiliar, does the ticket really exist.
   Each claim becomes VERIFIED, FAILED or NOT_CHECKABLE. Opinions are never "verified". Failed claims stay
   visible with the reason.
6. The benign-twin test: two scenarios with the same unusual login. In scenario A an IT ticket explains it.
   In scenario B there is no record. A good system changes its conclusion only because the evidence changed.

## 4. What makes it different (honest version)
AI SOC products (e.g. Dropzone, Prophet) already investigate alerts and show evidence. UEBA/SIEM tools already
learn baselines. So "AI investigates logs" is NOT new. Our contribution is smaller and testable:
a deterministic claim verifier + a reproducible benign-twin evaluation, open source, runnable by anyone.
We compare three systems on the SAME model: (1) rules only, (2) plain LLM with logs pasted in,
(3) CyberImmune. We report real numbers and their limits. We do not claim real-world detection performance.

## 5. How it flows
```
synthetic logs (SQLite) -> baseline rules -> marked unusual events
question -> Nemotron (Nebius) <-> Python-validated read-only tools (max 6 rounds)
         -> structured claims (JSON) -> verifier -> VERIFIED / FAILED / NOT_CHECKABLE + audit trail
         -> Streamlit app (3 screens) + evaluation harness
```

## 6. The three screens
1. Timeline: events over time, unusual ones highlighted, full source record for each.
2. Investigation: tool calls, claims with green/red/grey badges, hypotheses, missing evidence, next steps.
3. Evaluation Lab: the twin scenarios, expected answer vs the three systems, metrics, limits.

## 7. What we are NOT building
Real data, automatic response actions, extra models or routing, a second "skeptic" AI pass (only if
everything else is finished), PDF reports, machine-learning anomaly models.

## 8. Official hackathon facts (read from the rules page on Oct 9, 2026 — re-check before submitting)
- Deadline: Oct 30, 2026, 10:00 am PDT = 10:30 pm IST. Our own target: submit Oct 28.
- Must make a runtime call to Nebius Token Factory (or run on Nebius AI Cloud) and use at least one NVIDIA
  open model.
- Four equally weighted criteria: Technological Implementation, Design, Potential Impact, Quality of the Idea.
- Required: hosted demo URL, public GitHub repo with OSI licence, README on how Nemotron/Token Factory are
  used, YouTube video under 3 minutes, track choice, feedback on the tools.
- Project must stay free to test until judging ends (Dec 15).
Rules: https://nebiusglobalaihackathon.devpost.com/rules

## 9. Build plan (today is Oct 11; you have 17 days to Oct 28)
| Phase | What | Target dates |
|---|---|---|
| 0 | Project setup + Nebius API test | Oct 11 |
| 1 | Synthetic data + baseline rules | Oct 12-13 |
| 2 | Read-only tools | Oct 14 |
| 3 | AI investigation loop | Oct 15-16 |
| 4 | Verifier | Oct 17-18 |
| 5 | Scenarios + evaluation | Oct 19-22 |
| 6 | Streamlit UI | Oct 23-24 |
| 7 | Hosted demo | Oct 25 |
| 8 | README and docs | Oct 26 |
| 9 | Video script + recording | Oct 27 |
| 10 | Final checks + submit | Oct 28 |
Oct 29-30 are buffer only. There is little slack, so follow the gates below.

## 10. Gates (what to cut if you fall behind)
- Phase 0: if tool calling fails, use the JSON fallback (Phase 3 explains it). Do not stay stuck.
- Oct 18: if the verifier is not working, stop everything else and fix it. It is the centerpiece.
- Oct 22: no extra features. Fewer scenarios (e.g. 16 instead of 28) is better than an unfinished UI.
- Oct 25: UI rough? Keep it plain but working.

## 11. Rules for working with the coding assistant
One phase at a time. Small steps. Run tests and read the real output. Never share or commit the API key.
Synthetic data only. Everything the AI says must be traceable to a record or marked as interpretation.
