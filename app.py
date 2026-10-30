"""
CyberImmune Streamlit UI - 3 Screens
1. Timeline: Events with baseline flags
2. Investigation: Claims with verification badges
3. Evaluation Lab: S1/S2/S3 comparison
"""
import json
import html
from pathlib import Path
from typing import Dict, List, Any, Optional

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

# Import project modules
import sys
sys.path.insert(0, str(Path(__file__).parent))

from src.database import connect
from src.scenario import load_scenario
from src.baseline import find_indicators
from src.evidence_verifier import verify_investigation, VerificationStatus
from src.schemas import Investigation, Claim, ClaimType, ConclusionLabel


# ============================================================
# Helpers
# ============================================================

@st.cache_data
def load_all_scenarios() -> List[Dict[str, Any]]:
    """Load all scenarios from data/scenarios/ and data/scenarios_handwritten/."""
    scenarios = []
    for dir_name in ["data/scenarios", "data/scenarios_handwritten"]:
        dir_path = Path(dir_name)
        if dir_path.exists():
            for fp in sorted(dir_path.glob("*.json")):
                with open(fp) as f:
                    scenarios.append(json.load(f))
    return scenarios


@st.cache_data
def load_results_index() -> Dict[str, List[Path]]:
    """Index all result files in results/."""
    idx = {"investigations": [], "verifications": [], "reports": []}
    results_dir = Path("results")
    if results_dir.exists():
        for fp in sorted(results_dir.glob("*.json")):
            if "report_" in fp.name:
                idx["reports"].append(fp)
            elif "verification" in fp.name:
                idx["verifications"].append(fp)
            else:
                idx["investigations"].append(fp)
    return idx


@st.cache_data
def load_evaluation_report(split: str) -> Optional[Dict[str, Any]]:
    """Load evaluation report for a split."""
    fp = Path(f"results/report_{split}.json")
    if fp.exists():
        with open(fp) as f:
            return json.load(f)
    return None


def load_scenario_safe(scenario_id: str) -> Optional[Dict[str, Any]]:
    """Load a single scenario by ID."""
    for dir_name in ["data/scenarios", "data/scenarios_handwritten"]:
        fp = Path(dir_name) / f"{scenario_id}.json"
        if fp.exists():
            with open(fp) as f:
                return json.load(f)
    return None


def load_investigation_result(scenario_id: str) -> Optional[Dict[str, Any]]:
    """Load investigation result for a scenario."""
    fp = Path(f"results/{scenario_id}.json")
    if fp.exists():
        with open(fp) as f:
            return json.load(f)
    return None


def load_verification_report(scenario_id: str) -> Optional[Dict[str, Any]]:
    """Load verification report for a scenario."""
    fp = Path(f"results/verification_{scenario_id}.json")
    if fp.exists():
        with open(fp) as f:
            return json.load(f)
    return None


def get_baseline_flags(conn, user_id: str, cutoff: str, window_start: str, window_end: str) -> List[Dict]:
    """Get baseline indicators for events in window."""
    return find_indicators(conn, user_id, cutoff, window_start, window_end)


def format_badge(status: str, reason: str = "") -> str:
    """Format a claim status badge with safe HTML."""
    colors = {
        "VERIFIED": "#00D4AA",
        "FAILED": "#FF6B6B",
        "NOT_CHECKABLE": "#888888",
    }
    color = colors.get(status, "#888888")
    tooltip = f' title="{html.escape(reason)}"' if reason else ""
    return f'<span style="background-color:{color};color:white;padding:2px 8px;border-radius:4px;font-size:0.8em;font-weight:bold;"{tooltip}>{status}</span>'


def escape_for_display(text: str) -> str:
    """Escape text for safe display in Streamlit."""
    return html.escape(str(text))


# ============================================================
# Screen 1: Timeline
# ============================================================

def render_timeline_screen():
    st.header("📅 Timeline")

    # Sidebar controls
    scenarios = load_all_scenarios()
    scenario_options = {s["scenario_id"]: s for s in scenarios}

    selected_id = st.sidebar.selectbox(
        "Select Scenario",
        options=list(scenario_options.keys()),
        format_func=lambda x: f"{x} ({scenario_options[x].get('category', '?')})"
    )

    if not selected_id:
        return

    scenario = scenario_options[selected_id]

    # Load scenario DB
    session = None
    try:
        from src.scenario import build_session
        session = build_session(scenario)

        # Get all events for focus user
        cursor = session.conn.cursor()
        focus_user = scenario["focus_user"]
        cursor.execute(
            "SELECT * FROM events WHERE user_id = ? ORDER BY ts",
            (focus_user,)
        )
        events = [dict(row) for row in cursor.fetchall()]

        # Get baseline indicators
        baseline_cutoff = scenario["baseline_cutoff"]
        window_start = min(e["ts"] for e in scenario["injected_events"])
        window_end = max(e["ts"] for e in scenario["injected_events"])
        indicators = find_indicators(session.conn, focus_user, baseline_cutoff, window_start, window_end)

        # Build indicator lookup
        indicator_by_event = {}
        for ind in indicators:
            indicator_by_event.setdefault(ind["event_id"], []).append(ind)

        # Prepare timeline data
        df_data = []
        for e in events:
            is_injected = e["event_id"] in [inj["event_id"] for inj in scenario["injected_events"]]
            event_indicators = indicator_by_event.get(e["event_id"], [])
            flagged = len(event_indicators) > 0

            df_data.append({
                "ts": e["ts"],
                "event_type": e["event_type"],
                "event_id": e["event_id"],
                "device_id": e["device_id"],
                "resource": e["resource"] or "",
                "outcome": e["outcome"],
                "injected": is_injected,
                "flagged": flagged,
                "indicators": ", ".join([i["rule"] for i in event_indicators]) if event_indicators else "",
                "details": e["details"],
            })

        df = pd.DataFrame(df_data)
        if df.empty:
            st.warning("No events found for this user.")
            return

        # Plotly timeline
        fig = go.Figure()

        # Normal events
        normal = df[~df["flagged"]]
        if not normal.empty:
            fig.add_trace(go.Scatter(
                x=normal["ts"],
                y=normal["event_type"],
                mode="markers",
                marker=dict(size=10, color="#4A90D9", symbol="circle"),
                name="Normal",
                customdata=normal[["event_id", "device_id", "resource", "outcome", "details", "indicators"]].values,
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    "Time: %{x}<br>"
                    "Type: %{y}<br>"
                    "Device: %{customdata[1]}<br>"
                    "Resource: %{customdata[2]}<br>"
                    "Outcome: %{customdata[3]}<br>"
                    "Details: %{customdata[4]}<br>"
                    "Indicators: %{customdata[5]}"
                    "<extra></extra>"
                ),
            ))

        # Flagged events
        flagged = df[df["flagged"]]
        if not flagged.empty:
            fig.add_trace(go.Scatter(
                x=flagged["ts"],
                y=flagged["event_type"],
                mode="markers",
                marker=dict(size=14, color="#FF6B6B", symbol="triangle-up"),
                name="Flagged by Baseline",
                customdata=flagged[["event_id", "device_id", "resource", "outcome", "details", "indicators"]].values,
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    "Time: %{x}<br>"
                    "Type: %{y}<br>"
                    "Device: %{customdata[1]}<br>"
                    "Resource: %{customdata[2]}<br>"
                    "Outcome: %{customdata[3]}<br>"
                    "Details: %{customdata[4]}<br>"
                    "Indicators: %{customdata[5]}"
                    "<extra></extra>"
                ),
            ))

        # Injected events (highlight)
        injected = df[df["injected"]]
        if not injected.empty:
            fig.add_trace(go.Scatter(
                x=injected["ts"],
                y=injected["event_type"],
                mode="markers",
                marker=dict(size=18, color="#FFD700", symbol="star", line=dict(width=2, color="#000")),
                name="Injected Anomaly",
                customdata=injected[["event_id", "device_id", "resource", "outcome", "details", "indicators"]].values,
                hovertemplate=(
                    "<b>%{customdata[0]} (INJECTED)</b><br>"
                    "Time: %{x}<br>"
                    "Type: %{y}<br>"
                    "Device: %{customdata[1]}<br>"
                    "Resource: %{customdata[2]}<br>"
                    "Outcome: %{customdata[3]}<br>"
                    "Details: %{customdata[4]}<br>"
                    "Indicators: %{customdata[5]}"
                    "<extra></extra>"
                ),
            ))

        fig.update_layout(
            title=f"Events for {focus_user} — Baseline cutoff: {baseline_cutoff[:19]}",
            xaxis_title="Time (UTC)",
            yaxis_title="Event Type",
            height=500,
            hovermode="closest",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )

        st.plotly_chart(fig, use_container_width=True)

        # Evidence panel
        st.subheader("🔍 Evidence Panel")
        selected_event = st.selectbox(
            "Select event to inspect",
            options=df["event_id"].tolist(),
            format_func=lambda x: f"{x} — {df[df['event_id']==x]['ts'].values[0]} — {df[df['event_id']==x]['event_type'].values[0]}"
        )

        if selected_event:
            event = df[df["event_id"] == selected_event].iloc[0]
            col1, col2 = st.columns([1, 1])

            with col1:
                st.markdown("**Event Record**")
                st.code(json.dumps({
                    "event_id": event["event_id"],
                    "ts": event["ts"],
                    "user_id": focus_user,
                    "event_type": event["event_type"],
                    "device_id": event["device_id"],
                    "resource": event["resource"] or None,
                    "outcome": event["outcome"],
                    "details": event["details"],
                }, indent=2), language="json")

            with col2:
                st.markdown("**Baseline Rules Fired**")
                indicators = indicator_by_event.get(selected_event, [])
                if indicators:
                    for ind in indicators:
                        st.markdown(
                            f"{format_badge('FAILED', ind['detail'])} "
                            f"**{ind['rule']}** — {escape_for_display(ind['detail'])}",
                            unsafe_allow_html=True
                        )
                else:
                    st.markdown(format_badge("VERIFIED", "No baseline rules fired"), unsafe_allow_html=True)

    finally:
        if session:
            session.conn.close()


# ============================================================
# Screen 2: Investigation
# ============================================================

def render_investigation_screen():
    st.header("🔬 Investigation")

    # Sidebar controls
    scenarios = load_all_scenarios()
    scenario_options = {s["scenario_id"]: s for s in scenarios}

    selected_id = st.sidebar.selectbox(
        "Select Scenario",
        options=list(scenario_options.keys()),
        format_func=lambda x: f"{x} ({scenario_options[x].get('category', '?')})"
    )

    if not selected_id:
        return

    scenario = scenario_options[selected_id]

    # Load investigation result
    inv_result = load_investigation_result(selected_id)
    verification = load_verification_report(selected_id)

    if not inv_result:
        st.warning(f"No investigation result found for {selected_id}. Run Phase 3 first.")
        return

    if inv_result.get("status") != "success" or not inv_result.get("investigation"):
        st.error(f"Investigation failed: {inv_result.get('status')}")
        st.json(inv_result)
        return

    investigation = inv_result["investigation"]
    verifications = verification["claim_verifications"] if verification else []

    # Build verification lookup
    ver_by_claim = {v["claim_id"]: v for v in verifications}

    # Question
    st.markdown(f"**Question:** {escape_for_display(investigation['question'])}")

    # Conclusion
    conclusion = investigation["conclusion"]
    label = conclusion["label"]
    label_colors = {
        "no_concern": "#00D4AA",
        "likely_benign": "#4A90D9",
        "unexplained": "#FFD700",
        "insufficient_evidence": "#FF6B6B",
    }
    label_color = label_colors.get(label, "#888888")

    st.markdown(
        f"**Conclusion:** "
        f'<span style="background-color:{label_color};color:white;padding:4px 12px;border-radius:4px;font-weight:bold;">{label}</span>',
        unsafe_allow_html=True
    )
    st.markdown(f"**Rationale:** {escape_for_display(conclusion['rationale'])}")

    # What verifier proves box
    st.markdown("---")
    st.markdown("""
    **What the verifier proves / does not prove:**
    - ✅ Proves: Cited event/record IDs exist; field values match; temporal order; device familiarity per baseline; context record existence.
    - ❌ Does NOT prove: Interpretations, hypotheses, or missing evidence claims. These are the model's opinions, not verified facts.
    - ⚠️ Provenance warning: A claim may be VERIFIED but cite IDs the model never retrieved (shown with warning).
    """)

    # Claims
    st.subheader("📋 Claims")
    for claim in investigation["claims"]:
        v = ver_by_claim.get(claim["claim_id"])
        status = v["status"] if v else "NOT_CHECKABLE"
        reason = v["explanation"] if v else "No verification available"

        with st.expander(f"{claim['claim_id']}: {escape_for_display(claim['text'])}"):
            col1, col2 = st.columns([1, 3])
            with col1:
                st.markdown(f"Status: {format_badge(status, reason)}", unsafe_allow_html=True)
                st.markdown(f"**Type:** {claim['claim_type']}")

            with col2:
                st.markdown(f"**Structured:** `{json.dumps(claim['structured'], indent=2)}`")

                if claim["cited_event_ids"]:
                    st.markdown(f"**Cited Events:** {', '.join(claim['cited_event_ids'])}")
                if claim["cited_record_ids"]:
                    st.markdown(f"**Cited Records:** {', '.join(claim['cited_record_ids'])}")

                if claim["limitations"]:
                    st.markdown(f"**Limitations:** {escape_for_display(claim['limitations'])}")

                # Provenance warning
                if v and v.get("provenance_ok") is False:
                    st.warning("⚠️ Provenance Warning: This claim cites IDs that were never retrieved by the model!")

                # Checks detail
                if v and v.get("checks_run"):
                    st.markdown("**Verification Checks:**")
                    for check in v["checks_run"]:
                        check_status = "✅" if check["passed"] else "❌"
                        st.markdown(f"  {check_status} **{check['level']}**: {escape_for_display(check['detail'])}")

                # Supporting/contradicting
                if claim["supports"]:
                    st.markdown(f"**Supports:** {', '.join(claim['supports'])}")
                if claim["contradicts"]:
                    st.markdown(f"**Contradicts:** {', '.join(claim['contradicts'])}")

    # Hypotheses
    if investigation["hypotheses"]:
        st.subheader("💡 Hypotheses")
        for hyp in investigation["hypotheses"]:
            with st.expander(f"{hyp['hypothesis_id']}: {escape_for_display(hyp['description'])}"):
                if hyp["supporting_claim_ids"]:
                    st.markdown(f"**Supporting:** {', '.join(hyp['supporting_claim_ids'])}")
                if hyp["contradicting_claim_ids"]:
                    st.markdown(f"**Contradicting:** {', '.join(hyp['contradicting_claim_ids'])}")

    # Missing evidence
    if investigation["missing_evidence"]:
        st.subheader("❓ Missing Evidence")
        for item in investigation["missing_evidence"]:
            st.markdown(f"- {escape_for_display(item)}")

    # Next steps
    if investigation["next_steps"]:
        st.subheader("👤 Next Steps for Human")
        for step in investigation["next_steps"]:
            st.markdown(f"- {escape_for_display(step)}")

    # Audit trail
    with st.expander("📜 Audit Trail"):
        for step in inv_result.get("audit_steps", []):
            st.json(step)


# ============================================================
# Screen 3: Evaluation Lab
# ============================================================

def render_evaluation_lab():
    st.header("🧪 Evaluation Lab")

    # Sidebar
    split = st.sidebar.radio("Split", ["dev", "test"], index=0)
    report = load_evaluation_report(split)

    if not report:
        st.warning(f"No evaluation report found for {split} split. Run Phase 5 first.")
        return

    metadata = report["metadata"]
    st.markdown(f"**Model:** {metadata.get('model', '?')}")
    st.markdown(f"**Prompt:** {metadata.get('prompt_version', '?')}")
    st.markdown(f"**Git:** {metadata.get('git_commit', '?')[:8]}")

    # Scenario selector
    scenarios = load_all_scenarios()
    scenario_by_id = {s["scenario_id"]: s for s in scenarios}

    # Get scenarios that have results in this report
    by_system = report.get("by_system", {})
    scenario_ids = set()
    for system_data in by_system.values():
        # We need to map back... for now just use all scenarios
        pass

    selected_id = st.sidebar.selectbox(
        "Select Scenario",
        options=list(scenario_by_id.keys()),
        format_func=lambda x: f"{x} ({scenario_by_id[x].get('category', '?')})"
    )

    if not selected_id:
        return

    scenario = scenario_by_id[selected_id]
    gt = scenario["ground_truth"]

    # Load results for this scenario
    inv_result = load_investigation_result(selected_id)
    verification = load_verification_report(selected_id)

    # Ground truth
    st.subheader("🎯 Ground Truth")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Expected Label:** {gt.get('expected_label', '?')}")
        st.markdown(f"**Key Events:** {', '.join(gt.get('key_event_ids', []))}")
    with col2:
        st.markdown(f"**Key Records:** {', '.join(gt.get('key_record_ids', []))}")
        st.markdown(f"**Notes:** {escape_for_display(gt.get('notes', ''))}")

    # System results
    st.subheader("🤖 System Results")

    for system in ["s1", "s2", "s3"]:
        system_key = system
        # Load scenario-specific result
        result = load_investigation_result(selected_id)
        if result and result.get("model_name", "").endswith(system) or system == "s1":
            pass  # Simplified for now

    # Metrics table from report
    st.subheader("📊 Metrics (from report)")

    by_system = report.get("by_system", {})
    if by_system:
        metrics_df = pd.DataFrame([
            {
                "System": sys,
                "Label Accuracy": f"{data.get('label_accuracy', 0):.1%}",
                "Valid Citation Rate": f"{data.get('valid_citation_rate', 0):.1%}",
                "Unsupported Claim Rate": f"{data.get('unsupported_claim_rate', 0):.1%}",
                "Evidence Recall": f"{data.get('evidence_recall', 0):.1%}",
                "Retrieval Recall": f"{data.get('retrieval_recall', 0):.1%}",
                "Over-Hedging": f"{data.get('over_hedging_rate', 0):.1%}",
                "Insufficient Recall": f"{data.get('insufficient_recall', 0):.1%}",
                "Injection Resisted": f"{data.get('injection_resisted', 0):.1%}",
                "FP Rate": f"{data.get('fp_rate', 0):.1%}",
                "FN Rate": f"{data.get('fn_rate', 0):.1%}",
                "Limit Reached": f"{data.get('limit_reached_rate', 0):.1%}",
                "N": data.get("n_scenarios", 0),
            }
            for sys, data in by_system.items()
        ])
        st.dataframe(metrics_df, use_container_width=True)

    by_category = report.get("by_category", {})
    if by_category:
        st.subheader("📈 By Category")
        cat_df = pd.DataFrame([
            {
                "Category": cat,
                "Label Accuracy": f"{data.get('label_accuracy', 0):.1%}",
                "Valid Citation Rate": f"{data.get('valid_citation_rate', 0):.1%}",
                "Unsupported Claim Rate": f"{data.get('unsupported_claim_rate', 0):.1%}",
                "Evidence Recall": f"{data.get('evidence_recall', 0):.1%}",
                "N": data.get("n_scenarios", 0),
            }
            for cat, data in sorted(by_category.items())
        ])
        st.dataframe(cat_df, use_container_width=True)

    # Limits paragraph
    st.subheader("⚠️ Limits")
    st.markdown("""
    This evaluation is **synthetic and template-generated** with a **small N** (28 scenarios).
    Categories and anomalies are **author-designed**, not discovered.
    The **model is non-deterministic** even at temperature=0.
    **"Needs attention" labels are author-defined** — not ground-truth attack labels.
    **Results do not show real-world detection performance.** They measure whether
    CyberImmune's architecture (tools + verifier) produces more grounded, better-calibrated
    investigations than the same model given pasted logs.
    """)


# ============================================================
# Main App
# ============================================================

def main():
    st.set_page_config(
        page_title="CyberImmune",
        page_icon="🛡️",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.title("🛡️ CyberImmune — AI Security Investigation with Deterministic Verification")

    # Screen selector
    screen = st.sidebar.radio(
        "Screen",
        ["📅 Timeline", "🔬 Investigation", "🧪 Evaluation Lab"],
        index=0,
    )

    if screen == "📅 Timeline":
        render_timeline_screen()
    elif screen == "🔬 Investigation":
        render_investigation_screen()
    elif screen == "🧪 Evaluation Lab":
        render_evaluation_lab()


if __name__ == "__main__":
    main()