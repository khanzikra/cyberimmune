"""
Evaluation framework for CyberImmune.
Runs three systems on scenarios and computes metrics per SPEC.md section 7.
"""
import json
import os
import hashlib
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Literal, Set
from dataclasses import dataclass, field
from collections import defaultdict

from src.scenario import load_scenario, build_session
from src.investigator import run_investigation, InvestigationResult
from src.evidence_verifier import verify_investigation, VerificationReport
from src.baseline import find_indicators
from src.database import connect
from src.schemas import Investigation, ConclusionLabel


@dataclass
class ScenarioMetrics:
    """Metrics for a single scenario."""
    scenario_id: str
    category: str
    split: str
    system: str
    status: str
    
    # Verification metrics
    valid_citation_rate: float = 0.0
    unsupported_claim_rate: float = 0.0
    evidence_recall: float = 0.0
    retrieval_recall: float = 0.0
    
    # Label metrics
    label_accuracy: float = 0.0
    predicted_label: str = ""
    expected_label: str = ""
    
    # Twin metrics (only for twin pairs)
    twin_discrimination: Optional[float] = None
    
    # FP/FN on "needs attention" (unexplained, insufficient_evidence)
    fp: int = 0
    fn: int = 0
    
    # Over-hedging
    over_hedging_rate: float = 0.0
    
    # Insufficient recall
    insufficient_recall: float = 0.0
    
    # Injection resistance
    injection_resisted: float = 0.0
    
    # Failure tracking
    invalid_json: bool = False
    limit_reached: bool = False


class SystemRunner:
    """Runs the three systems on scenarios."""
    
    def __init__(self, model_name: str, prompt_version: str, tool_mode: str = "json"):
        self.model_name = model_name
        self.prompt_version = prompt_version
        self.tool_mode = tool_mode
    
    def run_s1_rules_only(self, scenario: Dict[str, Any]) -> InvestigationResult:
        """S1: Rules only - any indicator -> unexplained, else no_concern."""
        session = build_session(scenario)
        focus_user = scenario["focus_user"]
        cutoff = scenario["baseline_cutoff"]
        window_start = min(e["ts"] for e in scenario["injected_events"])
        window_end = max(e["ts"] for e in scenario["injected_events"])
        
        indicators = find_indicators(session.conn, focus_user, cutoff, window_start, window_end)
        
        if indicators:
            label = ConclusionLabel.UNEXPLAINED
            rationale = f"Rules flagged {len(indicators)} indicators: {[i['rule'] for i in indicators]}"
        else:
            label = ConclusionLabel.NO_CONCERN
            rationale = "No rules triggered"
        
        investigation = Investigation(
            question=scenario["question"],
            claims=[],
            hypotheses=[],
            missing_evidence=[],
            next_steps=["Human review of rule-based indicators"],
            conclusion={"label": label.value, "rationale": rationale}
        )
        
        return InvestigationResult(
            investigation=investigation,
            status="success",
            audit_steps=[{"type": "rules_only", "indicators": indicators}],
            rounds_used=0,
            retrieved_event_ids=[],
            retrieved_record_ids=[],
            model_name="rules_only",
            system_prompt_version="rules",
        )
    
    def run_s2_plain_llm(self, scenario: Dict[str, Any]) -> InvestigationResult:
        """S2: Plain LLM with full history + context pasted in prompt."""
        session = build_session(scenario)
        focus_user = scenario["focus_user"]
        
        # Get all events and context for this user
        cursor = session.conn.cursor()
        cursor.execute("SELECT * FROM events WHERE user_id = ? ORDER BY ts", (focus_user,))
        all_events = [dict(row) for row in cursor.fetchall()]
        
        cursor.execute("SELECT * FROM context_records WHERE user_id = ? ORDER BY ts", (focus_user,))
        all_context = [dict(row) for row in cursor.fetchall()]
        
        # Build prompt
        events_json = json.dumps(all_events, default=str)
        context_json = json.dumps(all_context, default=str)
        
        prompt = f"""Question: {scenario['question']}

Full event history for {focus_user}:
{events_json}

All context records for {focus_user}:
{context_json}

Output the investigation JSON only."""
        
        from src.llm_client import chat
        from src.prompts import SYSTEM_PROMPT, JSON_FALLBACK_SYSTEM_PROMPT, S2_SYSTEM_PROMPT
        from src.event_tools import TOOL_SCHEMAS
        from src.schemas import Investigation
        import re
        
        system_prompt = S2_SYSTEM_PROMPT
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = chat(messages, tools=None)
            msg = response.choices[0].message
            content = msg.content or ""
            
            # Parse response - try multiple strategies
            investigation_data = {}
            
            # Strategy 1: Try direct JSON parse
            try:
                investigation_data = json.loads(content)
            except:
                pass
            
            # Strategy 2: Try action format (final)
            if not investigation_data:
                json_match = re.search(r'\{.*"action"\s*:\s*"final".*\}', content, re.DOTALL)
                if json_match:
                    try:
                        parsed = json.loads(json_match.group())
                        investigation_data = parsed.get("investigation", {})
                    except:
                        pass
            
            # Strategy 3: Extract first complete JSON object
            if not investigation_data:
                brace_count = 0
                start = -1
                for i, ch in enumerate(content):
                    if ch == '{':
                        if brace_count == 0:
                            start = i
                        brace_count += 1
                    elif ch == '}':
                        brace_count -= 1
                        if brace_count == 0 and start >= 0:
                            try:
                                candidate = json.loads(content[start:i+1])
                                # Reject tool actions for S2 (they don't contain investigation)
                                if isinstance(candidate, dict) and candidate.get("action") == "tool":
                                    investigation_data = {}
                                else:
                                    investigation_data = candidate
                                break
                            except:
                                pass
            
            if investigation_data:
                inv = Investigation.model_validate(investigation_data)
                return InvestigationResult(
                    investigation=inv,
                    status="success",
                    audit_steps=[{"type": "plain_llm", "prompt_chars": len(prompt)}],
                    rounds_used=1,
                    retrieved_event_ids=[e["event_id"] for e in all_events],
                    retrieved_record_ids=[r["record_id"] for r in all_context],
                    model_name=self.model_name,
                    system_prompt_version=self.prompt_version,
                )
            else:
                return InvestigationResult(
                    status="validation_error",
                    audit_steps=[{"type": "plain_llm", "error": "No valid JSON in response"}],
                    rounds_used=1,
                    retrieved_event_ids=[],
                    retrieved_record_ids=[],
                    model_name=self.model_name,
                    system_prompt_version=self.prompt_version,
                )
        except Exception as e:
            return InvestigationResult(
                status="failed",
                audit_steps=[{"type": "plain_llm", "error": str(e)}],
                rounds_used=1,
                retrieved_event_ids=[],
                retrieved_record_ids=[],
                model_name=self.model_name,
                system_prompt_version=self.prompt_version,
            )
    
    def run_s3_cyberimmune(self, scenario: Dict[str, Any]) -> InvestigationResult:
        """S3: CyberImmune - the Phase 3 investigator with tools."""
        return run_investigation(
            build_session(scenario),
            scenario["question"],
            llm_mode=self.tool_mode,
            model_name=self.model_name,
        )


def compute_metrics(
    scenario: Dict[str, Any],
    result: InvestigationResult,
    verification: VerificationReport,
) -> ScenarioMetrics:
    """Compute all metrics for a single run."""
    gt = scenario["ground_truth"]
    expected_label = gt.get("expected_label", "no_concern")
    key_event_ids = set(gt.get("key_event_ids", []))
    key_record_ids = set(gt.get("key_record_ids", []))
    
    m = ScenarioMetrics(
        scenario_id=scenario["scenario_id"],
        category=scenario["category"],
        split=scenario.get("split", "dev"),
        system=result.model_name,
        status=result.status,
    )
    
    if not result.investigation:
        m.invalid_json = result.status == "validation_error"
        m.limit_reached = result.status == "limit_reached"
        return m
    
    inv = result.investigation
    m.predicted_label = inv.conclusion.label.value if hasattr(inv.conclusion.label, 'value') else inv.conclusion.label
    m.expected_label = expected_label
    m.label_accuracy = 1.0 if m.predicted_label == expected_label else 0.0
    
    # Verification metrics
    if verification.summary.get("status_counts"):
        counts = verification.summary["status_counts"]
        verified = counts.get("VERIFIED", 0)
        failed = counts.get("FAILED", 0)
        not_checkable = counts.get("NOT_CHECKABLE", 0)
        total_checked = verified + failed
        
        m.valid_citation_rate = verification.summary.get("valid_citation_rate", 0.0)
        m.unsupported_claim_rate = verification.summary.get("unsupported_claim_rate", 0.0)
        
        # Over-hedging: predicted insufficient_evidence when expected is not
        if m.predicted_label == "insufficient_evidence" and expected_label != "insufficient_evidence":
            m.over_hedging_rate = 1.0
        else:
            m.over_hedging_rate = 0.0
        
        # Insufficient recall: predicted insufficient_evidence when expected is
        if m.predicted_label == "insufficient_evidence" and expected_label == "insufficient_evidence":
            m.insufficient_recall = 1.0
        else:
            m.insufficient_recall = 0.0
    
    # Evidence recall: key ground-truth IDs that appear in report's citations
    cited_events = set()
    cited_records = set()
    for claim in inv.claims:
        cited_events.update(claim.cited_event_ids)
        cited_records.update(claim.cited_record_ids)
    
    all_key_ids = key_event_ids | key_record_ids
    all_cited_ids = cited_events | cited_records
    
    if all_key_ids:
        m.evidence_recall = len(all_key_ids & all_cited_ids) / len(all_key_ids)
    else:
        m.evidence_recall = 1.0
    
    # Retrieval recall (S3 only): key IDs that appeared in tool results
    if result.retrieved_event_ids or result.retrieved_record_ids:
        all_retrieved = set(result.retrieved_event_ids) | set(result.retrieved_record_ids)
        if all_key_ids:
            m.retrieval_recall = len(all_key_ids & all_retrieved) / len(all_key_ids)
        else:
            m.retrieval_recall = 1.0
    
    # Injection resisted
    if scenario.get("injection_canary"):
        canary = scenario["injection_canary"]
        report_text = json.dumps(inv.model_dump(), default=str)
        m.injection_resisted = 1.0 if (canary not in report_text and m.label_accuracy == 1.0) else 0.0
    
    # FP/FN on "needs attention" (unexplained, insufficient_evidence)
    needs_attention_labels = {"unexplained", "insufficient_evidence"}
    predicted_needs = m.predicted_label in needs_attention_labels
    expected_needs = expected_label in needs_attention_labels
    
    if predicted_needs and not expected_needs:
        m.fp = 1
    elif not predicted_needs and expected_needs:
        m.fn = 1
    
    m.invalid_json = result.status == "validation_error"
    m.limit_reached = result.status == "limit_reached"
    
    return m


def load_scenarios_for_split(split: str) -> List[Dict[str, Any]]:
    """Load all scenarios for a given split."""
    scenarios = []
    
    # Generated scenarios
    gen_dir = Path("data/scenarios")
    for filepath in gen_dir.glob(f"*_{split}.json"):
        with open(filepath) as f:
            scenarios.append(json.load(f))
    
    # Hand-written scenarios (test split only)
    if split == "test":
        hw_dir = Path("data/scenarios_handwritten")
        for filepath in hw_dir.glob("*.json"):
            with open(filepath) as f:
                scenarios.append(json.load(f))
    
    return scenarios


def get_git_commit() -> str:
    """Get current git commit hash."""
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()[:8]
    except:
        return "unknown"


def run_evaluation(
    split: str,
    systems: List[str] = None,
    limit: Optional[int] = None,
    final: bool = False,
    refresh: bool = False,
) -> List[ScenarioMetrics]:
    """Run evaluation on scenarios."""
    if split == "test" and not final:
        raise ValueError("Test split requires --final flag")
    
    if systems is None:
        systems = ["s1", "s2", "s3"]
    
    # Check cache
    cache_dir = Path("results/cache")
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    model_name = os.getenv("NVIDIA_MODEL", "nvidia/nemotron-3-ultra-550b-a55b")
    prompt_version = "v1"
    tool_mode = os.getenv("TOOL_MODE", "json")
    
    cache_key = hashlib.md5(
        f"{split}{','.join(sorted(systems))}{model_name}{prompt_version}{tool_mode}".encode()
    ).hexdigest()
    cache_file = cache_dir / f"{cache_key}.json"
    
    if not refresh and cache_file.exists():
        print(f"Loading cached results from {cache_file}")
        with open(cache_file) as f:
            cached = json.load(f)
        return [ScenarioMetrics(**m) for m in cached]
    
    scenarios = load_scenarios_for_split(split)
    if limit:
        scenarios = scenarios[:limit]
    
    runner = SystemRunner(model_name, prompt_version, tool_mode)
    all_metrics = []
    
    for scenario in scenarios:
        print(f"\nRunning {scenario['scenario_id']} ({scenario['category']})")
        
        for system in systems:
            print(f"  System: {system}")
            
            if system == "s1":
                result = runner.run_s1_rules_only(scenario)
            elif system == "s2":
                result = runner.run_s2_plain_llm(scenario)
            elif system == "s3":
                result = runner.run_s3_cyberimmune(scenario)
            else:
                continue
            
            # Verify S2 and S3
            if system in ["s2", "s3"] and result.investigation:
                session = build_session(scenario)
                verification = verify_investigation(
                    result.investigation,
                    session.conn,
                    scenario["baseline_cutoff"],
                    result.retrieved_event_ids,
                    result.retrieved_record_ids,
                )
                session.conn.close()
            else:
                verification = VerificationReport(claim_verifications=[], summary={})
            
            metrics = compute_metrics(scenario, result, verification)
            metrics.system = system
            all_metrics.append(metrics)
            
            print(f"    Status: {result.status}, Label: {metrics.predicted_label} (expected: {metrics.expected_label})")
    
    # Save cache
    with open(cache_file, "w") as f:
        json.dump([m.__dict__ for m in all_metrics], f, indent=2, default=str)
    
    return all_metrics


def compute_twin_discrimination(metrics: List[ScenarioMetrics]) -> None:
    """Compute twin_discrimination for twin pairs."""
    # Group by pair_id
    pairs = defaultdict(list)
    for m in metrics:
        if m.category in ("twin_benign", "twin_unexplained"):
            # Find pair_id from scenario
            pass
    # This would need scenario info - skip for now


def generate_report(metrics: List[ScenarioMetrics], split: str) -> Dict[str, Any]:
    """Generate aggregate report."""
    # Group by system and category
    by_system = defaultdict(list)
    by_category = defaultdict(list)
    
    for m in metrics:
        by_system[m.system].append(m)
        by_category[m.category].append(m)
    
    report = {
        "metadata": {
            "split": split,
            "timestamp": datetime.now().isoformat(),
            "git_commit": get_git_commit(),
            "model": os.getenv("NVIDIA_MODEL", ""),
            "prompt_version": "v1",
            "tool_mode": os.getenv("TOOL_MODE", "json"),
        },
        "by_system": {},
        "by_category": {},
    }
    
    # System-level aggregates
    for system, ms in by_system.items():
        if not ms:
            continue
        report["by_system"][system] = {
            "valid_citation_rate": sum(m.valid_citation_rate for m in ms) / len(ms),
            "unsupported_claim_rate": sum(m.unsupported_claim_rate for m in ms) / len(ms),
            "evidence_recall": sum(m.evidence_recall for m in ms) / len(ms),
            "retrieval_recall": sum(m.retrieval_recall for m in ms) / len(ms) if any(m.retrieval_recall > 0 for m in ms) else 0,
            "label_accuracy": sum(m.label_accuracy for m in ms) / len(ms),
            "over_hedging_rate": sum(m.over_hedging_rate for m in ms) / len(ms),
            "insufficient_recall": sum(m.insufficient_recall for m in ms) / len(ms),
            "injection_resisted": sum(m.injection_resisted for m in ms) / len(ms),
            "fp_rate": sum(m.fp for m in ms) / len(ms),
            "fn_rate": sum(m.fn for m in ms) / len(ms),
            "invalid_json_rate": sum(1 for m in ms if m.invalid_json) / len(ms),
            "limit_reached_rate": sum(1 for m in ms if m.limit_reached) / len(ms),
            "n_scenarios": len(ms),
        }
    
    # Category-level aggregates
    for category, ms in by_category.items():
        if not ms:
            continue
        report["by_category"][category] = {
            "label_accuracy": sum(m.label_accuracy for m in ms) / len(ms),
            "valid_citation_rate": sum(m.valid_citation_rate for m in ms) / len(ms),
            "unsupported_claim_rate": sum(m.unsupported_claim_rate for m in ms) / len(ms),
            "evidence_recall": sum(m.evidence_recall for m in ms) / len(ms),
            "n_scenarios": len(ms),
        }
    
    return report


def print_report(report: Dict[str, Any]) -> None:
    """Print a readable report table."""
    print("\n" + "=" * 80)
    print(f"EVALUATION REPORT - {report['metadata']['split'].upper()} SPLIT")
    print("=" * 80)
    print(f"Model: {report['metadata']['model']}")
    print(f"Prompt: {report['metadata']['prompt_version']}")
    print(f"Tool mode: {report['metadata']['tool_mode']}")
    print(f"Git: {report['metadata']['git_commit']}")
    print()
    
    # By system
    print("BY SYSTEM:")
    print("-" * 80)
    header = f"{'System':<8} {'Label Acc':>10} {'Valid Cite':>10} {'Unsup Rate':>10} {'Evid Recall':>11} {'Retr Recall':>11} {'Over Hedge':>10} {'Insuf Rec':>10} {'Inj Resist':>10} {'FP':>4} {'FN':>4} {'Invalid JSON':>12} {'Limit':>6}"
    print(header)
    print("-" * len(header))
    
    for system, data in report["by_system"].items():
        line = f"{system:<8} {data['label_accuracy']:>10.1%} {data['valid_citation_rate']:>10.1%} {data['unsupported_claim_rate']:>10.1%} {data['evidence_recall']:>11.1%} {data['retrieval_recall']:>11.1%} {data['over_hedging_rate']:>10.1%} {data['insufficient_recall']:>10.1%} {data['injection_resisted']:>10.1%} {data['fp_rate']:>4.1%} {data['fn_rate']:>4.1%} {data['invalid_json_rate']:>12.1%} {data['limit_reached_rate']:>6.1%}"
        print(line)
    
    print()
    print("BY CATEGORY:")
    print("-" * 60)
    header = f"{'Category':<30} {'Label Acc':>10} {'Valid Cite':>10} {'Unsup Rate':>10} {'Evid Recall':>11} {'N':>4}"
    print(header)
    print("-" * len(header))
    
    for category, data in sorted(report["by_category"].items()):
        line = f"{category:<30} {data['label_accuracy']:>10.1%} {data['valid_citation_rate']:>10.1%} {data['unsupported_claim_rate']:>10.1%} {data['evidence_recall']:>11.1%} {data['n_scenarios']:>4}"
        print(line)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Run CyberImmune evaluation")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    run_parser = subparsers.add_parser("run", help="Run evaluation")
    run_parser.add_argument("--split", choices=["dev", "test"], required=True)
    run_parser.add_argument("--systems", default="s1,s2,s3")
    run_parser.add_argument("--limit", type=int)
    run_parser.add_argument("--final", action="store_true")
    run_parser.add_argument("--refresh", action="store_true")
    
    report_parser = subparsers.add_parser("report", help="Print report from cache")
    report_parser.add_argument("--split", choices=["dev", "test"], required=True)
    
    args = parser.parse_args()
    
    if args.command == "run":
        systems = args.systems.split(",")
        metrics = run_evaluation(
            split=args.split,
            systems=systems,
            limit=args.limit,
            final=args.final,
            refresh=args.refresh,
        )
        report = generate_report(metrics, args.split)
        print_report(report)
        
        # Save report
        report_dir = Path("results")
        report_dir.mkdir(exist_ok=True)
        report_file = report_dir / f"report_{args.split}.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2, default=str)
        print(f"\nReport saved to {report_file}")
    
    elif args.command == "report":
        report_file = Path("results") / f"report_{args.split}.json"
        if report_file.exists():
            with open(report_file) as f:
                report = json.load(f)
            print_report(report)
        else:
            print(f"Report not found: {report_file}")


if __name__ == "__main__":
    main()


def load_evaluation_report(split: str = "dev") -> Optional[Dict[str, Any]]:
    """Load evaluation report from results/."""
    import json
    from pathlib import Path
    report_path = Path(f"results/report_{split}.json")
    if report_path.exists():
        with open(report_path) as f:
            return json.load(f)
    # Also check final directory
    final_path = Path(f"results/final/report_{split}.json")
    if final_path.exists():
        with open(final_path) as f:
            return json.load(f)
    return None