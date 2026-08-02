from pathlib import Path
import argparse,json,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from autonomous_paper_runtime.multi_day_shadow_validation import MultiDayShadowValidation
def main():
 p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");a=p.parse_args();r=Path(a.repository_root).resolve()
 out=MultiDayShadowValidation().run(
  performance_result_path=r/"release/op2_05_to_op2_08/actual/shadow_performance_evaluation_result.json",
  validation_policy_path=r/"release/op2_09_to_op2_12/input/multi_day_validation_policy.json",
  multi_day_evidence_path=r/"release/op2_09_to_op2_12/input/multi_day_shadow_evidence.json",
  summary_path=r/"release/op2_09_to_op2_12/actual/multi_day_shadow_summary.json",
  signal_quality_path=r/"release/op2_09_to_op2_12/actual/shadow_signal_quality.json",
  risk_consistency_path=r/"release/op2_09_to_op2_12/actual/shadow_risk_consistency.json",
  continuation_decision_path=r/"release/op2_09_to_op2_12/actual/shadow_continuation_decision.json",
  validation_token_path=r/"release/op2_09_to_op2_12/actual/multi_day_shadow_validation_token.json",
  result_path=r/"release/op2_09_to_op2_12/actual/multi_day_shadow_validation_result.json")
 print(json.dumps(out,indent=2,sort_keys=True));print("RESULT_FILE="+out["result_path"]);return 0 if out["status"]=="PASS" else 2
if __name__=="__main__":raise SystemExit(main())
