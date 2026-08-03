import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from paper_runtime.end_to_end_paper_cycle_certification_v83_65_68 import (
    run_end_to_end_paper_cycle_certification,
)

parser = argparse.ArgumentParser()
parser.add_argument("--certify", action="store_true")
parser.add_argument("--observed-at", default="")
args = parser.parse_args()

actual = ROOT / "release/v83_65_to_v83_68/actual"
result = run_end_to_end_paper_cycle_certification(
    dispatcher_result_path=(
        ROOT / "release/v83_29_to_v83_32/actual/"
        "local_trigger_dispatcher_result.json"
    ),
    chain_result_path=(
        ROOT / "release/v83_33_to_v83_36/actual/"
        "trigger_recovery_dispatch_chain_result.json"
    ),
    retry_result_path=(
        ROOT / "release/v83_37_to_v83_40/actual/"
        "trigger_chain_retry_policy_result.json"
    ),
    runner_result_path=(
        ROOT / "release/v83_49_to_v83_52/actual/"
        "supervised_reentry_runner_result.json"
    ),
    completion_result_path=(
        ROOT / "release/v83_53_to_v83_56/actual/"
        "retry_cycle_completion_result.json"
    ),
    recovery_result_path=(
        ROOT / "release/v83_61_to_v83_64/actual/"
        "crash_recovery_restart_result.json"
    ),
    orchestrator_result_path=(
        ROOT / "release/v83_57_to_v83_60/actual/"
        "full_schedule_completion_orchestrator_result.json"
    ),
    policy_path=(
        ROOT / "release/v83_65_to_v83_68/input/"
        "end_to_end_paper_cycle_certification_policy.json"
    ),
    scenario_overrides_path=(
        ROOT / "release/v83_65_to_v83_68/input/"
        "end_to_end_paper_cycle_scenario_overrides.json"
    ),
    ledger_path=actual / "end_to_end_paper_cycle_certification_ledger.jsonl",
    certificate_path=(
        actual / "end_to_end_paper_cycle_certificate.json"
    ),
    dashboard_path=(
        actual / "end_to_end_paper_cycle_certification_dashboard_state.json"
    ),
    result_path=(
        actual / "end_to_end_paper_cycle_certification_result.json"
    ),
    certify=args.certify,
    observed_at_override=args.observed_at,
)

print(json.dumps(result, indent=2, sort_keys=True))
print("RESULT_FILE=" + result["result_path"])
raise SystemExit(0 if result["status"] == "PASS" else 2)
