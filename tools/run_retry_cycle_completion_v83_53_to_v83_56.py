import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from paper_runtime.retry_cycle_completion_v83_53_56 import (
    run_retry_cycle_completion,
)

parser = argparse.ArgumentParser()
parser.add_argument("--finalize", action="store_true")
parser.add_argument("--observed-at", default="")
args = parser.parse_args()

actual = ROOT / "release/v83_53_to_v83_56/actual"
result = run_retry_cycle_completion(
    runner_result_path=(
        ROOT / "release/v83_49_to_v83_52/actual/"
        "supervised_reentry_runner_result.json"
    ),
    runner_completion_path=(
        ROOT / "release/v83_49_to_v83_52/actual/"
        "supervised_reentry_runner_completion.json"
    ),
    runner_recovery_path=(
        ROOT / "release/v83_49_to_v83_52/actual/"
        "supervised_reentry_runner_recovery_snapshot.json"
    ),
    retry_policy_result_path=(
        ROOT / "release/v83_37_to_v83_40/actual/"
        "trigger_chain_retry_policy_result.json"
    ),
    retry_plan_path=(
        ROOT / "release/v83_37_to_v83_40/actual/"
        "trigger_retry_plan.json"
    ),
    original_recovery_path=(
        ROOT / "release/v83_29_to_v83_32/actual/"
        "local_trigger_dispatch_recovery_snapshot.json"
    ),
    trigger_plan_path=(
        ROOT / "release/v83_25_to_v83_28/actual/"
        "automatic_schedule_trigger_plan.json"
    ),
    policy_path=(
        ROOT / "release/v83_53_to_v83_56/input/"
        "retry_cycle_completion_policy.json"
    ),
    completion_ledger_path=actual / "retry_cycle_completion_ledger.jsonl",
    certificate_path=actual / "retry_cycle_completion_certificate.json",
    dashboard_path=actual / "retry_cycle_completion_dashboard_state.json",
    result_path=actual / "retry_cycle_completion_result.json",
    finalize=args.finalize,
    observed_at_override=args.observed_at,
)

print(json.dumps(result, indent=2, sort_keys=True))
print("RESULT_FILE=" + result["result_path"])
raise SystemExit(0 if result["status"] == "PASS" else 2)
