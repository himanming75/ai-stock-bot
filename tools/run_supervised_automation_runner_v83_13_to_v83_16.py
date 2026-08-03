
import argparse, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from paper_runtime.supervised_automation_runner_v83_13_16 import run_supervised_automation_runner

p = argparse.ArgumentParser()
p.add_argument("--execute-runner", action="store_true")
p.add_argument("--clear-runner-lock", action="store_true")
a = p.parse_args()

result = run_supervised_automation_runner(
    controlled_cycle_result_path=ROOT/"release/v83_09_to_v83_12/actual/controlled_automation_cycle_result.json",
    orchestrator_result_path=ROOT/"release/v83_01_to_v83_04/actual/automated_orchestrator_result.json",
    dispatcher_result_path=ROOT/"release/v83_05_to_v83_08/actual/local_action_dispatcher_result.json",
    risk_result_path=ROOT/"release/v82_13_to_v82_16/actual/shadow_risk_controller_result.json",
    policy_path=ROOT/"release/v83_13_to_v83_16/input/supervised_automation_runner_policy.json",
    runner_lock_path=ROOT/"release/v83_13_to_v83_16/actual/supervised_automation_runner.lock.json",
    runner_ledger_path=ROOT/"release/v83_13_to_v83_16/actual/supervised_automation_runner_ledger.jsonl",
    runner_summary_path=ROOT/"release/v83_13_to_v83_16/actual/supervised_automation_runner_summary.json",
    recovery_path=ROOT/"release/v83_13_to_v83_16/actual/supervised_automation_runner_recovery.json",
    dashboard_path=ROOT/"release/v83_13_to_v83_16/actual/supervised_automation_runner_dashboard_state.json",
    result_path=ROOT/"release/v83_13_to_v83_16/actual/supervised_automation_runner_result.json",
    execute_runner=a.execute_runner,
    clear_runner_lock=a.clear_runner_lock,
)
print(json.dumps(result, indent=2, sort_keys=True))
print("RESULT_FILE=" + result["result_path"])
raise SystemExit(0 if result["status"] == "PASS" else 2)
