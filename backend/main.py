"""
CyberImmune FastAPI Backend
Thin API layer that imports existing src/ modules.
Also serves the Vue frontend in production.
"""
import os
import sys
from pathlib import Path
from typing import Optional

# Add project root and src to path - handles both local and Render paths
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from src.scenario_gen import load_scenarios
from src.scenario import load_scenario, build_session
from src.baseline import compute_baseline, find_indicators
from src.investigator import run_investigation
from src.evidence_verifier import verify_investigation
from src.schemas import Investigation
from src.llm_client import LLMClient
from src.evaluation import run_evaluation, load_evaluation_report

# Environment
ENABLE_LIVE = os.getenv("ENABLE_LIVE", "0") == "1"
LIVE_DAILY_CAP = int(os.getenv("LIVE_DAILY_CAP", "10"))
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")

# Frontend build directory (for production)
FRONTEND_DIR = Path(__file__).parent.parent / "frontend" / "dist"

# In-memory live run tracking
live_run_state = {
    "running": False,
    "daily_count": 0,
    "last_reset": None,
}


app = FastAPI(
    title="CyberImmune API",
    description="AI Security Investigator with Deterministic Verification",
    version="1.0.0",
)


@app.on_event("startup")
async def startup_event():
    print("CyberImmune API starting up...")


@app.on_event("shutdown")
async def shutdown_event():
    print("CyberImmune API shutting down...")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# --- Models ---
class ScenarioSummary(BaseModel):
    scenario_id: str
    category: str
    split: str
    pair_id: Optional[str] = None
    pair_role: Optional[str] = None


class EventRecord(BaseModel):
    event_id: str
    ts: str
    user_id: str
    event_type: str
    device_id: Optional[str] = None
    resource: Optional[str] = None
    source_ip: Optional[str] = None
    outcome: str
    details_untrusted: str


class ContextRecord(BaseModel):
    record_id: str
    ts: str
    user_id: str
    record_type: str
    device_id: Optional[str] = None
    summary_untrusted: str
    status: str


class ScenarioResult(BaseModel):
    scenario_id: str
    question: str
    focus_user: str
    baseline_cutoff: str
    events: List[EventRecord]
    context_records: List[ContextRecord]
    investigation: Optional[Dict[str, Any]] = None
    verification: Optional[Dict[str, Any]] = None
    audit_steps: Optional[List[Dict[str, Any]]] = None
    status: str
    rounds_used: int


class LiveRunRequest(BaseModel):
    scenario_id: str


class LiveRunResponse(BaseModel):
    run_id: str
    status: str
    message: str


# --- Endpoints ---
@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "cyberimmune-api"}


@app.get("/api/scenarios", response_model=List[ScenarioSummary])
async def list_scenarios(
    split: Optional[str] = Query(None, description="Filter by split: dev or test"),
    category: Optional[str] = Query(None, description="Filter by category"),
):
    """List all scenarios (without ground truth)."""
    scenarios = load_scenarios("dev") + load_scenarios("test")
    
    # Add handwritten scenarios
    import json
    from pathlib import Path
    handwritten_dir = Path("data/scenarios_handwritten")
    if handwritten_dir.exists():
        for f in handwritten_dir.glob("*.json"):
            with open(f) as fh:
                scenarios.append(json.load(fh))
    
    result = []
    for s in scenarios:
        if split and s.get("split") != split:
            continue
        if category and s.get("category") != category:
            continue
        result.append(ScenarioSummary(
            scenario_id=s["scenario_id"],
            category=s["category"],
            split=s["split"],
            pair_id=s.get("pair_id"),
            pair_role=s.get("pair_role"),
        ))
    
    return result


@app.get("/api/scenarios/{scenario_id}/result", response_model=ScenarioResult)
async def get_scenario_result(scenario_id: str):
    """Get cached investigation result + events + context for a scenario."""
    # Load scenario
    try:
        if scenario_id.startswith("heldout_"):
            import json
            from pathlib import Path
            path = Path("data/scenarios_handwritten") / f"{scenario_id}.json"
            with open(path) as f:
                scenario = json.load(f)
        else:
            scenario = load_scenario(f"data/scenarios/{scenario_id}.json")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Scenario {scenario_id} not found")
    
    # Build session and get events
    session = build_session(scenario)
    
    # Get all events for focus user
    cur = session.conn.execute("""
        SELECT * FROM events WHERE user_id = ? ORDER BY ts, event_id
    """, (scenario["focus_user"],))
    events = [dict(row) for row in cur.fetchall()]
    
    # Get context records
    cur = session.conn.execute("""
        SELECT * FROM context_records WHERE user_id = ? ORDER BY ts, record_id
    """, (scenario["focus_user"],))
    context_records = [dict(row) for row in cur.fetchall()]
    
    # Load cached investigation result
    investigation = None
    verification = None
    audit_steps = None
    status = "no_result"
    rounds_used = 0
    
    import json
    from pathlib import Path
    result_paths = [
        Path(f"results/final/{scenario_id}.json"),
        Path(f"results/demo.json"),
    ]
    for p in result_paths:
        if p.exists():
            with open(p) as f:
                result = json.load(f)
                if result.get("investigation"):
                    investigation = result["investigation"]
                    verification = result.get("verification")
                    audit_steps = result.get("audit_steps")
                    status = result.get("status", "success")
                    rounds_used = result.get("rounds_used", 0)
                break
    
    # Format events for frontend
    formatted_events = []
    for e in events:
        formatted_events.append(EventRecord(
            event_id=e["event_id"],
            ts=e["ts"],
            user_id=e["user_id"],
            event_type=e["event_type"],
            device_id=e["device_id"],
            resource=e["resource"],
            source_ip=e["source_ip"],
            outcome=e["outcome"],
            details_untrusted=e.get("details", "")[:200],
        ))
    
    formatted_context = []
    for c in context_records:
        formatted_context.append(ContextRecord(
            record_id=c["record_id"],
            ts=c["ts"],
            user_id=c["user_id"],
            record_type=c["record_type"],
            device_id=c["device_id"],
            summary_untrusted=c.get("summary", "")[:200],
            status=c["status"],
        ))
    
    return ScenarioResult(
        scenario_id=scenario_id,
        question=scenario["question"],
        focus_user=scenario["focus_user"],
        baseline_cutoff=scenario["baseline_cutoff"],
        events=formatted_events,
        context_records=formatted_context,
        investigation=investigation,
        verification=verification,
        audit_steps=audit_steps,
        status=status,
        rounds_used=rounds_used,
    )


@app.get("/api/evaluation/report")
async def get_evaluation_report(split: str = Query("dev")):
    """Get the evaluation report."""
    report = load_evaluation_report(split)
    if not report:
        raise HTTPException(status_code=404, detail=f"No evaluation report for split {split}")
    return report


# --- Live Investigation Endpoint ---
@app.post("/api/investigations", response_model=LiveRunResponse)
async def run_live_investigation(request: LiveRunRequest):
    """Run a live investigation (requires ENABLE_LIVE=1)."""
    if not ENABLE_LIVE:
        raise HTTPException(status_code=403, detail="Live mode disabled. Set ENABLE_LIVE=1 to enable.")
    
    # Check daily cap
    from datetime import datetime, date
    today = date.today()
    if live_run_state["last_reset"] != today:
        live_run_state["daily_count"] = 0
        live_run_state["last_reset"] = today
    
    if live_run_state["daily_count"] >= LIVE_DAILY_CAP:
        raise HTTPException(status_code=429, detail=f"Daily limit of {LIVE_DAILY_CAP} live runs reached")
    
    if live_run_state["running"]:
        raise HTTPException(status_code=409, detail="Another live investigation is already running")
    
    # Load scenario
    try:
        if request.scenario_id.startswith("heldout_"):
            import json
            from pathlib import Path
            path = Path("data/scenarios_handwritten") / f"{request.scenario_id}.json"
            with open(path) as f:
                scenario = json.load(f)
        else:
            scenario = load_scenario(f"data/scenarios/{request.scenario_id}.json")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Scenario {request.scenario_id} not found")
    
    # Run investigation in background (simplified - in production use background tasks)
    live_run_state["running"] = True
    try:
        session = build_session(scenario)
        llm = LLMClient()
        result = run_investigation(session, scenario["question"], llm=llm, mode="native")
        
        live_run_state["daily_count"] += 1
        
        # Save result
        from pathlib import Path
        Path("results").mkdir(exist_ok=True)
        with open(f"results/{scenario_id}_live.json", "w") as f:
            import json
            json.dump(result.model_dump(mode="json"), f, indent=2)
        
        return LiveRunResponse(
            run_id=f"live_{request.scenario_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            status=result.status,
            message=f"Investigation completed with status: {result.status}"
        )
    except Exception as e:
        return LiveRunResponse(
            run_id="",
            status="error",
            message=f"Investigation failed: {str(e)}"
        )
    finally:
        live_run_state["running"] = False


# --- Serve Vue Frontend in Production ---
if FRONTEND_DIR.exists():
    # Serve static assets (JS, CSS, images)
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")
    
    # Serve other static files (favicon, etc.)
    @app.get("/{path:path}")
    async def serve_frontend(path: str):
        """SPA fallback - serve index.html for all non-API routes"""
        # Don't intercept API routes
        if path.startswith("api/"):
            raise HTTPException(status_code=404, detail="API endpoint not found")
        
        file_path = FRONTEND_DIR / path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        
        # Fallback to index.html for SPA routing
        index_path = FRONTEND_DIR / "index.html"
        if index_path.exists():
            return FileResponse(index_path)
        
        raise HTTPException(status_code=404, detail="Frontend not built. Run `npm run build` in frontend/")
else:
    @app.get("/{path:path}")
    async def frontend_not_built(path: str):
        if path.startswith("api/"):
            raise HTTPException(status_code=404, detail="API endpoint not found")
        raise HTTPException(status_code=503, detail="Frontend not built. Run `npm run build` in frontend/")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)