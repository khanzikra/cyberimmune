"""
CyberImmune Streamlit App - Three screens for investigation transparency.
Screen 1: Timeline - events with baseline flags
Screen 2: Investigation - claims with verification badges
Screen 3: Evaluation Lab - S1/S2/S3 comparison
"""
import json
import html
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

# Add src to path
import sys
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.scenario_gen import load_scenarios
from src.scenario import load_scenario, build_session
from src.baseline import compute_baseline, find_indicators
from src.schemas import Investigation, ClaimType, ConclusionLabel
from src.evidence_verifier import verify_investigation


# Page config
st.set_page_config(
    page_title="CyberImmune - AI Security Investigator",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for badges and styling
st.markdown("""
<style>
.badge-verified { background-color: #00D4AA; color: #0E1117; padding: 2px 8px; border-radius: 4px; font-weight: 600; font-size: 0.8rem; display: inline-block; }
.badge-failed { background-color: #FF6B6B; color: #0E1117; padding: 2px 8px; border-radius: 4px; font-weight: 600; font-size: 0.8rem; display: inline-block; }
.badge-not-checkable { background-color: #888888; color: #FAFAFA; padding: 2px 8px; border-radius: 4px; font-weight: 600; font-size: 0.8rem; display: inline-block; }
.badge-warning { background-color: #FFA500; color: #0E1117; padding: 2px 8px; border-radius: 4px; font-weight: 600; font-size: 0.75rem; display: inline-block; margin-left: 8px; }
.claim-box { border-left: 3px solid #333; padding: 12px; margin: 8px 0; background-color: #1E2329; }
.claim-box.verified { border-left-color: #00D4AA; }
.claim-box.failed { border-left-color: #FF6B6B; }
.claim-box.not-checkable { border-left-color: #888888; }
.stText, .stCode { background-color: #1E2329 !important; }
</style>
""", unsafe_allow_html=True)


@st.cache_data
def load_all_scenarios():
    """Load all scenarios from data/scenarios and data/scenarios_handwritten."""
    scenarios = load_scenarios("dev") + load_scenarios("test")
    handwritten_dir = Path("data/scenarios_handwritten")
    if handwritten_dir.exists():
        for f in handwritten_dir.glob("*.json"):
            with open(f) as fh:
                scenarios.append(json.load(fh))
    return {s["scenario_id"]: s for s in scenarios}


@st.cache_data
def load_evaluation_report(split: str = "dev"):
    """Load evaluation report from results/."""
    report_path = Path(f"results/report_{split}.json")
    if report_path.exists():
        with open(report_path) as f:
            return json.load(f)
    return None


@st.cache_data
def load_investigation_result(scenario_id: str):
    """Load investigation result from results/."""
    result_path = Path(f"results/{scenario_id}.json")
    if result_path.exists():
        with open(result_path) as f:
            return json.load(f)
    # Also check demo result
    demo_path = Path("results/demo.json")
    if demo_path.exists() and scenario_id == "demo_twin_A":
        with open(demo_path) as f:
            return json.load(f)
    return None


@st.cache_data
def build_session_for_scenario(scenario: Dict):
    """Build a ToolSession for a scenario (cached)."""
    session = build_session(scenario)
    return session


def get_event_color(event_type: str, is_flagged: bool) -> str:
    """Get color for event based on type and flagged status."""
    if is_flagged:
        return "#FF6B6B"  # Red for flagged
    colors = {
        "login": "#00D4AA",
        "resource_access": "#4ECDC4",
        "password_reset": "#FFD93D",
        "mfa_challenge": "#6C5CE7",
    }
    return colors.get(event_type, "#888888")


def render_timeline_screen(scenario: Dict, session):
    """Screen 1: Timeline of events with baseline flags."""
    st.header("📅 Timeline - Focus User Events")

    focus_user = scenario["focus_user"]
    cutoff = scenario["baseline_cutoff"]

    # Get all events for focus user
    cur = session.conn.execute("""
        SELECT * FROM events WHERE user_id = ? ORDER BY ts, event_id
    """, (focus_user,))
    events = [dict(row) for row in cur.fetchall()]

    if not events:
        st.warning("No events found for this user.")
        return

    # Compute baseline and indicators
    baseline = compute_baseline(session.conn, focus_user, cutoff)
    indicators = find_indicators(session.conn, focus_user, cutoff,
                                  "2024-01-22T00:00:00Z", "2024-01-31T23:59:59Z")

    # Build indicator lookup
    flagged_event_ids = {ind["event_id"] for ind in indicators}
    indicator_details = {ind["event_id"]: ind for ind in indicators}

    # Create Plotly timeline
    df = pd.DataFrame(events)
    df["ts"] = pd.to_datetime(df["ts"])
    df["is_flagged"] = df["event_id"].isin(flagged_event_ids)
    df["color"] = df.apply(lambda r: get_event_color(r["event_type"], r["is_flagged"]), axis=1)
    df["hover_text"] = df.apply(
        lambda r: f"{r['event_id']}<br>{r['ts']}<br>{r['event_type']}<br>Device: {r['device_id']}<br>Resource: {r['resource']}<br>Outcome: {r['outcome']}",
        axis=1
    )

    fig = go.Figure()

    for event_type in df["event_type"].unique():
        subset = df[df["event_type"] == event_type]
        fig.add_trace(go.Scatter(
            x=subset["ts"],
            y=[event_type] * len(subset),
            mode="markers",
            marker=dict(
                size=12,
                color=subset["color"],
                symbol="circle",
                line=dict(width=2, color="white" if "is_flagged" in subset.columns and subset["is_flagged"].any() else "rgba(0,0,0,0)")
            ),
            name=event_type,
            text=subset["hover_text"],
            hoverinfo="text",
            showlegend=True,
        ))

    # Add cutoff line
    fig.add_vline(
        x=cutoff,
        line_dash="dash",
        line_color="#FFA500",
        annotation_text="Baseline Cutoff",
        annotation_position="top"
    )

    fig.update_layout(
        title=f"Events for {focus_user} (Baseline: {baseline['baseline_login_count']} logins, sufficient: {baseline['baseline_sufficient']})",
        xaxis_title="Time (UTC)",
        yaxis_title="Event Type",
        height=500,
        hovermode="closest",
        plot_bgcolor="#0E1117",
        paper_bgcolor="#0E1117",
        font_color="#FAFAFA",
    )

    st.plotly_chart(fig, use_container_width=True)

    # Evidence panel for selected event
    st.subheader("Evidence Panel")
    event_ids = [e["event_id"] for e in events]
    selected_event_id = st.selectbox("Select event to inspect:", event_ids)

    if selected_event_id:
        event = next(e for e in events if e["event_id"] == selected_event_id)
        is_flagged = selected_event_id in flagged_event_ids

        col1, col2 = st.columns([2, 1])

        with col1:
            st.code(f"""
Event ID: {event['event_id']}
Timestamp: {event['ts']}
User: {event['user_id']}
Event Type: {event['event_type']}
Device: {event['device_id']}
Resource: {event['resource']}
Source IP: {event['source_ip']}
Outcome: {event['outcome']}
Details: {html.escape(event['details'])}
            """, language="text")

        with col2:
            if is_flagged:
                ind = indicator_details[selected_event_id]
                st.error(f"🚨 **Flagged by {ind['rule']}**")
                st.write(ind["detail"])
            else:
                st.success("✅ No baseline rules triggered")

            # Show which rules could apply
            st.markdown("**Applicable Rules:**")
            st.markdown("""
- **R1 unusual_hour**: Login hour ≤ 2% of baseline logins
- **R2 new_device**: Device never seen before cutoff
- **R3 rare_resource**: Resource accessed ≤ 1 time before cutoff
- **R4 failure_burst**: ≥ 3 failed logins in 10 minutes
            """)


def render_investigation_screen(scenario: Dict, session):
    """Screen 2: Investigation with verified claims."""
    st.header("🔍 Investigation")

    result = load_investigation_result(scenario["scenario_id"])

    if not result:
        st.warning("No investigation result found for this scenario. Run Phase 3 first.")
        return

    if result.get("status") != "success" or not result.get("investigation"):
        st.error(f"Investigation status: {result.get('status', 'unknown')}")
        if result.get("error"):
            st.code(result["error"])
        return

    inv = result["investigation"]

    # Load verification report
    verification = None
    if "verification" in result and result["verification"]:
        verification = result["verification"]
    else:
        # Run verification on the fly
        inv_obj = Investigation(**inv)
        report = verify_investigation(
            inv_obj,
            session.conn,
            scenario["baseline_cutoff"],
            retrieved_event_ids=result.get("retrieved_event_ids", []),
            retrieved_record_ids=result.get("retrieved_record_ids", []),
        )
        verification = report.to_dict()

    # Question
    st.markdown(f"**Question:** {inv['question']}")

    # Conclusion with colored badge
    conclusion = inv["conclusion"]
    label = conclusion["label"]
    rationale = conclusion["rationale"]

    label_colors = {
        "no_concern": "🟢",
        "likely_benign": "🟡",
        "unexplained": "🟠",
        "insufficient_evidence": "🔵",
    }
    label_emoji = label_colors.get(label, "⚪")

    st.markdown(f"### Conclusion: {label_emoji} **{label.replace('_', ' ').title()}**")
    st.markdown(f"*Rationale:* {rationale}")

    # What the verifier proves box
    with st.expander("ℹ️ What the verifier proves / does not prove", expanded=True):
        st.markdown("""
**The verifier PROVES (machine-checkable):**
- ✅ An event ID exists in the database
- ✅ A field value matches the database (timestamp, device, resource, etc.)
- ✅ Event A happened strictly before Event B
- ✅ A device was/was not seen in the baseline period
- ✅ A context record exists with matching user/type

**The verifier does NOT prove (interpretive):**
- ❌ Whether an anomaly is an attack or benign
- ❌ Whether a hypothesis is correct
- ❌ Whether missing evidence would change the conclusion
- ❌ Any claim of "compromised", "attacked", "breach", or "malicious"

**Failed claims are never hidden** - they remain visible with the failure reason.
""")

    # Claims with verification badges
    st.markdown("---")
    st.subheader("Claims")

    claims = inv.get("claims", [])
    claim_verifications = {cv["claim_id"]: cv for cv in verification.get("claim_verifications", [])}

    for claim in claims:
        claim_id = claim["claim_id"]
        cv = claim_verifications.get(claim_id, {})
        status = cv.get("status", "NOT_CHECKABLE")
        explanation = cv.get("explanation", "No verification data")

        # Determine badge
        if status == "VERIFIED":
            badge_html = '<span class="badge-verified">✓ VERIFIED</span>'
            box_class = "verified"
        elif status == "FAILED":
            badge_html = '<span class="badge-failed">✗ FAILED</span>'
            box_class = "failed"
        else:
            badge_html = '<span class="badge-not-checkable">⚬ NOT_CHECKABLE</span>'
            box_class = "not-checkable"

        # Provenance warning
        provenance_warning = ""
        if cv.get("provenance_ok") is False:
            provenance_warning = '<span class="badge-warning">⚠ Provenance: cited ID not in retrieved set</span>'

        # Build claim box
        with st.container():
            st.markdown(f"""
<div class="claim-box {box_class}">
    <strong>{claim_id}</strong> {badge_html} {provenance_warning}
    <br><br>
    <strong>Text:</strong> {html.escape(claim['text'])}
    <br>
    <strong>Type:</strong> {claim['claim_type']}
    <br>
    <strong>Cited Events:</strong> {', '.join(claim.get('cited_event_ids', [])) or '—'}
    <br>
    <strong>Cited Records:</strong> {', '.join(claim.get('cited_record_ids', [])) or '—'}
    <br>
    <strong>Structured:</strong> {json.dumps(claim.get('structured', {}))}
    <br>
    <strong>Supports:</strong> {', '.join(claim.get('supports', [])) or '—'}
    <br>
    <strong>Contradicts:</strong> {', '.join(claim.get('contradicts', [])) or '—'}
    <br>
    <strong>Limitations:</strong> {html.escape(claim.get('limitations', ''))}
    <br>
    <strong>Verification:</strong> {status} — {explanation}
</div>
            """, unsafe_allow_html=True)

    # Hypotheses
    if inv.get("hypotheses"):
        st.markdown("---")
        st.subheader("Hypotheses")
        for hyp in inv["hypotheses"]:
            st.markdown(f"**{hyp['hypothesis_id']}**: {html.escape(hyp['description'])}")
            if hyp.get("supporting_claim_ids"):
                st.caption(f"Supporting: {', '.join(hyp['supporting_claim_ids'])}")
            if hyp.get("contradicting_claim_ids"):
                st.caption(f"Contradicting: {', '.join(hyp['contradicting_claim_ids'])}")

    # Missing evidence
    if inv.get("missing_evidence"):
        st.markdown("---")
        st.subheader("Missing Evidence")
        for item in inv["missing_evidence"]:
            st.markdown(f"- {html.escape(item)}")

    # Next steps
    if inv.get("next_steps"):
        st.markdown("---")
        st.subheader("Next Steps (Human Actions Only)")
        for step in inv["next_steps"]:
            st.markdown(f"- {html.escape(step)}")

    # Tool calls / audit steps
    if result.get("audit_steps"):
        with st.expander("🔧 Tool Calls & Audit Trail"):
            for step in result["audit_steps"]:
                step_type = step.get("step", "")
                if step_type == "model_tool_call":
                    st.markdown(f"**Tool Call:** `{step.get('tool')}` with args `{step.get('args')}`")
                elif step_type == "tool_result":
                    status = "✅" if step.get("ok") else "❌"
                    st.markdown(f"{status} **Tool Result:** `{step.get('tool')}` — rows: {step.get('row_count')}" + (f" — error: {step.get('error')}" if step.get("error") else ""))
                elif step_type == "validation_error":
                    st.markdown(f"❌ **Validation Error (attempt {step.get('attempt')}):** {step.get('error')}")
                elif step_type == "model_response":
                    preview = step.get("content_preview", "")[:200]
                    if preview:
                        st.markdown(f"**Model Response:** {html.escape(preview)}...")


def render_evaluation_lab(scenarios: Dict, report: Optional[Dict]):
    """Screen 3: Evaluation Lab - S1/S2/S3 comparison."""
    st.header("🧪 Evaluation Lab")

    if not report:
        st.warning("No evaluation report found. Run Phase 5 evaluation first.")
        return

    # Scenario selector for detailed view
    scenario_ids = [s["scenario_id"] for s in scenarios.values()]
    selected_scenario_id = st.selectbox("Select scenario for detailed view:", scenario_ids)

    if selected_scenario_id:
        scenario = scenarios[selected_scenario_id]
        st.markdown(f"### {selected_scenario_id} ({scenario['category']})")
        st.markdown(f"**Question:** {scenario['question']}")

        # Ground truth
        gt = scenario["ground_truth"]
        st.markdown(f"**Ground Truth:** `{gt['expected_label']}` — {gt.get('notes', '')}")

        # System results
        col1, col2, col3 = st.columns(3)
        for col, system in zip([col1, col2, col3], ["s1", "s2", "s3"]):
            with col:
                st.markdown(f"#### {system.upper()}")
                sys_data = None
                for r in report["results"]:
                    if r["scenario"]["scenario_id"] == selected_scenario_id:
                        sys_data = r.get(system)
                        break

                if sys_data:
                    inv = sys_data.get("investigation")
                    if inv:
                        pred = inv.get("conclusion", {}).get("label", "N/A")
                        st.markdown(f"**Prediction:** `{pred}`")

                        # Citation validity
                        verif = sys_data.get("verification", {})
                        summary = verif.get("summary", {})
                        st.metric("Valid Citations", f"{summary.get('valid_citation_rate', 0):.1%}")
                        st.metric("Unsupported Claims", f"{summary.get('unsupported_claim_rate', 0):.1%}")
                    else:
                        st.markdown(f"**Status:** {sys_data.get('status', 'N/A')}")
                        if sys_data.get("error"):
                            st.caption(f"Error: {sys_data['error'][:100]}")
                else:
                    st.markdown("*No result*")

    # Overall metrics table
    st.markdown("---")
    st.subheader("Overall Metrics (Dev Split)")

    overall = report.get("overall", {})
    if overall:
        metrics_df = pd.DataFrame([
            {
                "System": sys,
                "Evidence Recall": f"{m.get('evidence_recall', 0):.1%}",
                "Retrieval Recall": f"{m.get('retrieval_recall', 0):.1%}",
                "Label Accuracy": f"{m.get('label_accuracy', 0):.1%}",
                "FP": m.get('fp', 0),
                "FN": m.get('fn', 0),
                "Over-Hedging": f"{m.get('over_hedging_rate', 0):.1%}",
                "Insufficient Recall": f"{m.get('insufficient_recall', 0):.1%}",
                "Injection Resisted": f"{m.get('injection_resisted', 0):.0%}",
                "Twin Discrimination": f"{m.get('twin_discrimination', 0):.1%}",
            }
            for sys, m in overall.items()
        ])
        st.dataframe(metrics_df, use_container_width=True, hide_index=True)

    # Twin discrimination detail
    st.markdown("---")
    st.subheader("Twin Discrimination")
    twin = report.get("twin_discrimination", {})
    for sys, data in twin.items():
        st.markdown(f"- **{sys}**: {data.get('pairs_correct', 0)}/{data.get('pairs_evaluated', 0)} pairs correct = {data.get('twin_discrimination', 0):.1%}")

    # Category breakdown
    st.markdown("---")
    st.subheader("Per-Category Metrics")
    cat_metrics = report.get("category_metrics", {})
    for sys in ["s1", "s2", "s3"]:
        with st.expander(f"{sys.upper()} by Category"):
            for cat, data in cat_metrics.get(sys, {}).items():
                avg = data.get("avg_metrics", {})
                st.markdown(f"**{cat}** (n={data['count']})")
                st.markdown(f"  Label Acc: {avg.get('label_accuracy', 0):.1%} | "
                           f"Evidence Recall: {avg.get('evidence_recall', 0):.1%} | "
                           f"Injection Resist: {avg.get('injection_resisted', 0):.0%}")

    # Limits paragraph
    with st.expander("📋 Evaluation Limits", expanded=False):
        with open("EVALUATION_NOTES.md") as f:
            limits_text = f.read()
        st.markdown(limits_text[:3000] + "..." if len(limits_text) > 3000 else limits_text)


def main():
    # Sidebar
    st.sidebar.title("🛡️ CyberImmune")
    st.sidebar.caption("AI Security Investigator with Deterministic Verification")

    # Load data
    scenarios = load_all_scenarios()
    report_dev = load_evaluation_report("dev")
    report_test = load_evaluation_report("test")

    # Scenario selector
    scenario_ids = sorted(scenarios.keys())
    default_idx = 0
    if "demo_twin_A" in scenario_ids:
        default_idx = scenario_ids.index("demo_twin_A")
    selected_scenario_id = st.sidebar.selectbox(
        "Scenario:",
        scenario_ids,
        index=default_idx,
        format_func=lambda x: f"{x} ({scenarios[x]['category']})"
    )
    scenario = scenarios[selected_scenario_id]

    # Screen selector
    screen = st.sidebar.radio(
        "Screen:",
        ["1. Timeline", "2. Investigation", "3. Evaluation Lab"],
        index=0
    )

    # Build session for selected scenario
    session = build_session_for_scenario(scenario)

    # Render selected screen
    if screen == "1. Timeline":
        render_timeline_screen(scenario, session)
    elif screen == "2. Investigation":
        render_investigation_screen(scenario, session)
    elif screen == "3. Evaluation Lab":
        render_evaluation_lab(scenarios, report_dev)

    # Footer
    st.sidebar.markdown("---")
    st.sidebar.caption("CyberImmune — Nebius x NVIDIA Hackathon 2026")
    st.sidebar.caption("Deterministic verification • No live LLM calls in UI")


if __name__ == "__main__":
    main()