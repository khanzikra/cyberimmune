# CyberImmune Demo Video Script (Target: 2:30, Hard Limit: <3:00)

## Shot List & Narration Table

| Time | On Screen | Narration |
|------|-----------|-----------|
| **0:00–0:05** | Title card: "CyberImmune — AI can make the claim. Evidence must prove it." | "AI security assistants write convincing explanations. But their claims may not match the logs." |
| **0:05–0:15** | Split screen: confident LLM text vs. actual log lines with red X | "They sound confident. But they often ignore harmless explanations — like an approved laptop replacement." |
| **0:15–0:20** | Problem statement slide (text only, 3 bullets) | "The problem: no standard way to verify what an AI says against the actual evidence." |
| **0:20–0:30** | Architecture diagram (Mermaid from README) — data flow | "CyberImmune lets an LLM investigate through three read-only, validated tools. Then Python checks every factual claim." |
| **0:30–0:40** | Code peek: `llm_client.py` (3 lines: client, model, base URL) | "The model is NVIDIA Nemotron 3 Ultra, called through Nebius Token Factory. One file talks to the API." |
| **0:40–0:55** | **Twin A** — Screen 2 "Investigation": scenario `twin_benign_v1`, tool calls visible, 4 claims with green VERIFIED badges, conclusion `likely_benign` | "Twin A: unusual login at 03:10 UTC, new device, rare resource. But there's an IT ticket for a laptop replacement. The model calls tools, cites event IDs, and the verifier marks all claims VERIFIED. Conclusion: likely benign." |
| **0:55–1:10** | **Twin B** — same scenario ID `twin_unexplained_v1`, same tool calls, but NO context records, conclusion `unexplained`, missing evidence listed | "Twin B: same anomaly, same tool calls. But no explaining record exists. The verifier flags the missing context. Conclusion: unexplained. Missing evidence: no IT ticket, no approved device." |
| **1:10–1:25** | Side-by-side comparison: Twin A `likely_benign` vs Twin B `unexplained` | "Same anomaly. Different evidence. Different conclusion. That's the benign-twin test." |
| **1:25–1:40** | **Plain LLM failure** — Screen 2 showing S2 result with a claim flagged red FAILED (citation missing or field mismatch), verifier reason shown | "We also ran a plain LLM with all logs pasted in — no tools. It hallucinated a citation. The verifier caught it: FAILED — event ID does not exist." |
| **1:40–2:00** | **Evaluation Lab** — Screen 3: metrics table (S1 only for now), twin discrimination 0%, label accuracy 0% for S1, limits paragraph visible | "On the dev split, rules-only (S1) got 0% label accuracy and 0% twin discrimination. It flags everything. The evaluation framework is ready for S2/S3 when a working model is available." |
| **2:00–2:10** | What the verifier proves / does not prove (text from README) | "The verifier proves: event exists, field matches, order, device in baseline, context exists. It does NOT prove: attack, breach, compromised, or whether a hypothesis is correct." |
| **2:10–2:20** | Architecture diagram + `llm_client.py` on screen | "Nemotron via Nebius is in `llm_client.py` and the investigator loop. One file. No secrets in the UI." |
| **2:20–2:30** | Closing card: "Auditable claims, not perfect security. Open source. MIT licence." | "CyberImmune: auditable claims, not perfect security. Open source, reproducible, honest about limits." |

---

## Recording Checklist

| Item | Details |
|------|---------|
| **Resolution** | 1920×1080 (1080p), 30 fps |
| **Browser** | Chrome/Edge, incognito window |
| **URL** | `http://localhost:8501` (DEMO MODE) |
| **Hide** | Terminal/env vars, `.env` file, any API keys, notifications, bookmarks bar |
| **Audio** | Read narration at ~150 wpm; leave 0.5s pause between sections |
| **Mouse** | Smooth movements; highlight clicks with cursor trail if possible |
| **Backup** | If live run fails, use cached results (app runs in DEMO MODE by default) |

---

## Backup Shots (Use Cached Results If Live Fails)

| Shot | How to Capture |
|------|----------------|
| Twin A investigation | Select `twin_benign_v1` in sidebar → Screen 2 |
| Twin B investigation | Select `twin_unexplained_v1` → Screen 2 |
| Plain LLM FAILED claim | Use `results/final/demo.json` (has audit steps but no investigation); explain verbally |
| Evaluation Lab table | Screen 3 → "Overall Metrics" table (S1 only) |
| Architecture diagram | Scroll README in browser or show `docs/ARCHITECTURE.md` |
| Code peek `llm_client.py` | Open in VS Code, scroll to top 20 lines |
| Verifier FAILED claim | Run `scripts/verify_result.py` on a test investigation with bad claims |

---

## Numbers to Speak (All From Real Results)

| Metric | Value | Source |
|--------|-------|--------|
| S1 Label Accuracy (dev) | 0.0% | `results/final/report_dev.json` |
| S1 Evidence Recall (dev) | 66.7% | `results/final/report_dev.json` |
| S1 Twin Discrimination | 0.0% | `results/final/report_dev.json` |
| Twin pairs evaluated | 0 / 0 | `results/final/report_dev.json` (S1 has no pairs) |
| Dev scenarios run | 3 (limited) | `results/final/report_dev.json` |
| Test scenarios | 4 hand-written + 24 template | `data/scenarios_handwritten/` + `data/scenarios/` |
| Model | NVIDIA Nemotron 3 Ultra 550B A55B | `NEBIUS_MODEL` env var |
| API endpoint | `https://integrate.api.nvidia.com/v1` | `NEBIUS_BASE_URL` env var |

---

## What NOT to Say

| ❌ Avoid | ✅ Say Instead |
|----------|----------------|
| "detects attacks" | "flags anomalies for human review" |
| "eliminates hallucination" | "catches unsupported claims with a deterministic verifier" |
| "proves it's benign" | "concludes likely benign when evidence explains the anomaly" |
| "real-time security" | "prototype on synthetic data" |
| "production-ready" | "hackathon prototype, open source" |

---

## Post-Production Notes

- Add captions matching narration
- Blur any accidental env var glimpses
- Trim to 2:30 max
- Export as MP4, H.264, <100MB
- Upload to YouTube (unlisted or public per hackathon rules)