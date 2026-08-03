import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from paper_runtime.reentry_execution_guard_audit_v83_45_48 import run_reentry_execution_guard_audit
p=argparse.ArgumentParser()
p.add_argument("--prepare-execution",action="store_true")
p.add_argument("--execute-mode",action="store_true")
p.add_argument("--clear-execution-lock",action="store_true")
p.add_argument("--observed-at",default="")
a=p.parse_args(); actual=ROOT/"release/v83_45_to_v83_48/actual"
r=run_reentry_execution_guard_audit(
 approval_result_path=ROOT/"release/v83_41_to_v83_44/actual/retry_approval_supervised_reentry_result.json",
 approval_lock_path=ROOT/"release/v83_41_to_v83_44/actual/retry_approval.lock.json",
 reentry_plan_path=ROOT/"release/v83_41_to_v83_44/actual/supervised_reentry_plan.json",
 retry_plan_path=ROOT/"release/v83_37_to_v83_40/actual/trigger_retry_plan.json",
 retry_lock_path=ROOT/"release/v83_37_to_v83_40/actual/trigger_retry.lock.json",
 policy_path=ROOT/"release/v83_45_to_v83_48/input/reentry_execution_guard_policy.json",
 execution_lock_path=actual/"reentry_execution.lock.json",
 audit_ledger_path=actual/"reentry_execution_audit_ledger.jsonl",
 execution_plan_path=actual/"reentry_execution_plan.json",
 recovery_snapshot_path=actual/"reentry_execution_guard_recovery_snapshot.json",
 dashboard_path=actual/"reentry_execution_guard_audit_dashboard_state.json",
 result_path=actual/"reentry_execution_guard_audit_result.json",
 prepare_execution=a.prepare_execution,dry_run=not a.execute_mode,
 clear_execution_lock=a.clear_execution_lock,observed_at_override=a.observed_at)
print(json.dumps(r,indent=2,sort_keys=True)); print("RESULT_FILE="+r["result_path"])
raise SystemExit(0 if r["status"]=="PASS" else 2)
