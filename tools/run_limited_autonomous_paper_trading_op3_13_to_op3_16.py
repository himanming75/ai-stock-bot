from pathlib import Path
import argparse, json, sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from autonomous_paper_runtime.limited_autonomous_paper_trading import (
    PAPER_BASE_URL,LimitedAutonomousPaperTrading,
)
def main():
 p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");p.add_argument("--enable-network",action="store_true");p.add_argument("--enable-submission",action="store_true");p.add_argument("--approval-phrase",default="");p.add_argument("--base-url",default=PAPER_BASE_URL);a=p.parse_args();r=Path(a.repository_root).resolve()
 out=LimitedAutonomousPaperTrading().run(
  lifecycle_result_path=r/"release/op3_09_to_op3_12/actual/paper_order_lifecycle_result.json",
  runtime_policy_path=r/"release/op3_13_to_op3_16/input/limited_autonomous_runtime_policy.json",
  signal_snapshot_path=r/"release/op3_13_to_op3_16/input/limited_autonomous_signal_snapshot.json",
  risk_snapshot_path=r/"release/op3_13_to_op3_16/input/limited_autonomous_risk_snapshot.json",
  account_snapshot_path=r/"release/op3_13_to_op3_16/input/limited_autonomous_account_snapshot.json",
  runtime_state_path=r/"release/op3_13_to_op3_16/actual/limited_autonomous_runtime_state.json",
  decision_path=r/"release/op3_13_to_op3_16/actual/limited_autonomous_decision.json",
  submission_receipt_path=r/"release/op3_13_to_op3_16/actual/limited_autonomous_submission_receipt.json",
  runtime_ledger_path=r/"release/op3_13_to_op3_16/actual/limited_autonomous_runtime_ledger.jsonl",
  completion_token_path=r/"release/op3_13_to_op3_16/actual/limited_autonomous_completion_token.json",
  result_path=r/"release/op3_13_to_op3_16/actual/limited_autonomous_paper_trading_result.json",
  enable_network=a.enable_network,enable_submission=a.enable_submission,
  approval_phrase=a.approval_phrase,base_url=a.base_url)
 print(json.dumps(out,indent=2,sort_keys=True));print("RESULT_FILE="+out["result_path"]);return 0 if out["status"]=="PASS" else 2
if __name__=="__main__":raise SystemExit(main())
