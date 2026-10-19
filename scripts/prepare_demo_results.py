"""
Script to prepare final cached results for demo mode.
Copies dev/test evaluation reports and example investigations to results/final/
"""
import json
import shutil
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.scenario_gen import load_scenarios


def prepare_demo_results():
    """Copy all necessary files to results/final/ for demo mode."""
    final_dir = Path("results/final")
    final_dir.mkdir(parents=True, exist_ok=True)

    # 1. Copy evaluation reports
    for split in ["dev", "test"]:
        src = Path(f"results/report_{split}.json")
        if src.exists():
            dst = final_dir / f"report_{split}.json"
            shutil.copy2(src, dst)
            print(f"Copied {src} -> {dst}")

    # 2. Copy demo investigation result
    demo_src = Path("results/demo.json")
    if demo_src.exists():
        shutil.copy2(demo_src, final_dir / "demo.json")
        print(f"Copied {demo_src} -> {final_dir / 'demo.json'}")

    # 3. Copy scenario files needed for UI (scenario metadata + injected events)
    scenarios_dir = final_dir / "scenarios"
    scenarios_dir.mkdir(parents=True, exist_ok=True)

    scenarios = load_scenarios("dev") + load_scenarios("test")
    # Add handwritten
    handwritten_dir = Path("data/scenarios_handwritten")
    if handwritten_dir.exists():
        for f in handwritten_dir.glob("*.json"):
            with open(f) as fh:
                scenarios.append(json.load(fh))

    for s in scenarios:
        # Save minimal scenario data needed for UI (no ground truth for judges)
        demo_scenario = {
            "scenario_id": s["scenario_id"],
            "category": s["category"],
            "pair_id": s.get("pair_id"),
            "pair_role": s.get("pair_role"),
            "split": s["split"],
            "question": s["question"],
            "focus_user": s["focus_user"],
            "baseline_cutoff": s["baseline_cutoff"],
            "injected_events": s.get("injected_events", []),
            "context_records": s.get("context_records", []),
            "injection_canary": s.get("injection_canary"),
            # NOTE: ground_truth is intentionally omitted for demo mode
        }
        with open(scenarios_dir / f"{s['scenario_id']}.json", "w") as f:
            json.dump(demo_scenario, f, indent=2)

    print(f"Saved {len(scenarios)} demo scenarios to {scenarios_dir}")

    # 4. Create a manifest
    manifest = {
        "generated_at": "2026-10-19",
        "description": "Cached results for CyberImmune demo mode (synthetic, key-free)",
        "reports": ["report_dev.json", "report_test.json"],
        "investigations": ["demo.json"],
        "scenarios_count": len(scenarios),
    }
    with open(final_dir / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"\nDemo results prepared in {final_dir}")
    print("Contents:")
    for f in sorted(final_dir.rglob("*")):
        if f.is_file():
            print(f"  {f.relative_to(final_dir)} ({f.stat().st_size} bytes)")


if __name__ == "__main__":
    prepare_demo_results()