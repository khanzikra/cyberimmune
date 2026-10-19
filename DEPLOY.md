# DEPLOY.md — Deploying CyberImmune to Streamlit Community Cloud

## Overview
This guide walks through deploying the CyberImmune demo to **Streamlit Community Cloud** (free, no credit card required). The app runs in **DEMO MODE** by default (cached results, no API keys). Optional **LIVE MODE** requires `ENABLE_LIVE=1` and Nebius credentials.

---

## Prerequisites
- GitHub account
- GitHub repo: `https://github.com/khanzikra/cyberimmune` (your fork)
- Streamlit Community Cloud account: https://share.streamlit.io (sign in with GitHub)

---

## Step 1: Prepare the Repository

The repo is already ready with:
- `app.py` — main entry point
- `requirements.txt` — pinned dependencies
- `.streamlit/config.toml` — dark theme config
- `results/final/` — cached demo results (synthetic, key-free)
- `.gitignore` — excludes `.env`, `venv/`, `*.db`

**Verify locally first:**
```bash
# Fresh clone test
git clone https://github.com/khanzikra/cyberimmune.git
cd cyberimmune
python -m venv venv
venv\Scripts\pip.exe install -r requirements.txt
venv\Scripts\streamlit run app.py
# Should open at http://localhost:8501 in DEMO MODE
```

---

## Step 2: Deploy on Streamlit Community Cloud

1. Go to **https://share.streamlit.io** and sign in with GitHub
2. Click **"New app"**
3. Configure:
   - **Repository**: `khanzikra/cyberimmune`
   - **Branch**: `master` (or `main`)
   - **Main file path**: `app.py`
   - **Python version**: 3.11 or 3.12
4. Click **"Deploy!"**

The app will build and deploy. First build takes 2-3 minutes.

---

## Step 3: Configure Secrets (Optional - for LIVE MODE only)

**DEMO MODE works without any secrets.** Skip this unless you want LIVE MODE.

If you want LIVE MODE:
1. In Streamlit Cloud dashboard, go to your app → **Settings** → **Secrets**
2. Add:
   ```toml
   NEBIUS_API_KEY = "your-nebius-api-key"
   NEBIUS_BASE_URL = "https://integrate.api.nvidia.com/v1"
   NEBIUS_MODEL = "nvidia/nemotron-3-ultra-550b-a55b"
   ENABLE_LIVE = "1"
   LIVE_DAILY_CAP = "10"
   ```
3. Click **Save** → app will restart in LIVE MODE

**Security notes:**
- Never commit `.env` or secrets to GitHub
- Streamlit secrets are encrypted at rest
- Only the app process can read them via `st.secrets` or `os.getenv`
- Keys are never exposed to the browser

---

## Step 4: Test the Deployed URL

1. After deployment, copy the **public URL** (e.g., `https://khanzikra-cyberimmune.streamlit.app`)
2. Open in a **private/incognito browser window** (to test without cookies)
3. Verify:
   - App loads in **DEMO MODE** (green badge in sidebar)
   - All 3 screens work: Timeline, Investigation, Evaluation Lab
   - Scenario selector shows 28 scenarios
   - Plotly timeline renders
   - Investigation claims show verification badges
   - Evaluation Lab shows metrics table

---

## Step 5: Verify It Stays Available

- Streamlit Community Cloud free tier keeps apps running indefinitely
- Apps sleep after 7 days of inactivity but wake on first request (~30s cold start)
- Judging ends **Dec 15, 2026** — app will stay available
- No credit card or billing needed for free tier

---

## Optional: Deploy to Nebius AI Cloud

If you prefer Nebius over Streamlit Cloud:

1. Create a **Nebius AI Cloud** account
2. Create a **Compute** instance (GPU not needed for demo)
3. Clone repo, install deps, run:
   ```bash
   streamlit run app.py --server.port 8501 --server.address 0.0.0.0
   ```
4. Use Nebius Load Balancer or SSH tunnel to expose port 8501
5. Set `ENABLE_LIVE=1` and add secrets via Nebius secret manager

**Note:** Streamlit Community Cloud is recommended for simplicity and zero cost.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Build fails on `requirements.txt` | Check Python version (3.11/3.12), all deps are pinned |
| App shows blank screen | Check Streamlit logs in Cloud dashboard for errors |
| `ModuleNotFoundError` | Ensure all imports use `sys.path.insert(0, "src")` |
| Plotly not rendering | Verify `plotly` in requirements.txt |
| DEMO MODE not loading | Check `results/final/` exists in repo (it should) |

---

## Checklist Before Submitting Hackathon

- [ ] Fresh clone + `pip install -r requirements.txt` + `streamlit run app.py` works locally
- [ ] Deployed URL opens in private browser window
- [ ] All 3 screens render with cached data
- [ ] No `.env` or secrets in repo (`git status` clean)
- [ ] `results/final/` committed with cached results
- [ ] `DEPLOY.md` followed and URL tested
- [ ] YouTube demo video recorded (< 3 min)
- [ ] GitHub repo public with OSI license (MIT/Apache-2.0)
- [ ] Hackathon submission form filled with URL, video, repo

---

## Support

- Streamlit Cloud docs: https://docs.streamlit.io/streamlit-community-cloud
- Streamlit Community Cloud status: https://status.streamlit.io
- For hackathon questions: check Discord/Slack or email organizers

---

**Demo URL (once deployed):** `https://<your-app-name>.streamlit.app`

**Keep this URL for your hackathon submission!**