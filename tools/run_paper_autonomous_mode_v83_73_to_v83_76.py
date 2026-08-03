import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from paper_runtime.paper_autonomous_mode_v83_73_76 import (
    run_paper_autonomous_mode,
)

parser = argparse.ArgumentParser()
parser.add_argument("--authorize-autonomous-cycle", action="store_true")
parser.add_argument("--complete-cycle", action="store_true")
parser.add_argument("--clear-autonomous-lock", action="store_true")
parser.add_argument("--observed-at", default="")
args = parser.parse_args()

actual = ROOT / "release/v83_73_to_v83_76/actual"
result = run_paper_autonomous_mode(
    control_center_result_path=(
        ROOT / "release/v83_69_to_v83_72/actual/"
        "operator_control_center_result.json"
    ),
    certification_result_path=(
        ROOT / "release/v83_65_to_v83_68/actual/"
        "end_to_end_paper_cycle_certification_result.json"
    ),
    orchestrator_result_path=(
        ROOT / "release/v83_57_to_v83_60/actual/"
        "full_schedule_completion_orchestrator_result.json"
    ),
    recovery_result_path=(
        ROOT / "release/v83_61_to_v83_64/actual/"
        "crash_recovery_restart_result.json"
    ),
    policy_path=(
        ROOT / "release/v83_73_to_v83_76/input/"
        "paper_autonomous_mode_policy.json"
    ),
    autonomous_lock_path=actual / "paper_autonomous_mode.lock.json",
    autonomous_plan_path=actual / "paper_autonomous_cycle_plan.json",
    autonomous_ledger_path=actual / "paper_autonomous_mode_ledger.jsonl",
    dashboard_path=actual / "paper_autonomous_mode_dashboard_state.json",
    result_path=actual / "paper_autonomous_mode_result.json",
    authorize_autonomous_cycle=args.authorize_autonomous_cycle,
    complete_cycle=args.complete_cycle,
    clear_autonomous_lock=args.clear_autonomous_lock,
    observed_at_override=args.observed_at,
)

print(json.dumps(result, indent=2, sort_keys=True))
print("RESULT_FILE=" + result["result_path"])
raise SystemExit(0 if result["status"] == "PASS" else 2)
