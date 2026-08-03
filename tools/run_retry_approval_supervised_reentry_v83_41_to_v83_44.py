import argparse, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from paper_runtime.retry_approval_supervised_reentry_v83_41_44 import run_retry_approval_supervised_reentry
p=argparse.ArgumentParser()
p.add_argument("--approve-retry",action="store_true")
p.add_argument("--complete-reentry",action="store_true")
p.add_argument("--clear-approval-lock",action="store_true")
p.add_argument("--observed-at",default="")
a=p.parse_args()
actual=ROOT/"release/v83_41_to_v83_44/actual"
r=run_retry_approval_supervised_reentry(
 retry_policy_result_path=ROOT/"release/v83_37_to_v83_40/actual/trigger_chain_retry_policy_result.json",
 retry_plan_path=ROOT/"release/v83_37_to_v83_40/actual/trigger_retry_plan.json",
 retry_lock_path=ROOT/"release/v83_37_to_v83_40/actual/trigger_retry.lock.json",
 approval_policy_path=ROOT/"release/v83_41_to_v83_44/input/retry_approval_policy.json",
 approval_lock_path=actual/"retry_approval.lock.json",
 approval_ledger_path=actual/"retry_approval_ledger.jsonl",
 reentry_plan_path=actual/"supervised_reentry_plan.json",
 dashboard_path=actual/"retry_approval_supervised_reentry_dashboard_state.json",
 result_path=actual/"retry_approval_supervised_reentry_result.json",
 approve_retry=a.approve_retry, complete_reentry=a.complete_reentry,
 clear_approval_lock=a.clear_approval_lock, observed_at_override=a.observed_at)
print(json.dumps(r,indent=2,sort_keys=True)); print("RESULT_FILE="+r["result_path"])
raise SystemExit(0 if r["status"]=="PASS" else 2)
