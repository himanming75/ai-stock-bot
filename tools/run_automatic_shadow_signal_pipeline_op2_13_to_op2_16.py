from pathlib import Path
import argparse,json,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from autonomous_paper_runtime.automatic_shadow_signal_pipeline import AutomaticShadowSignalPipeline
def main():
 p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");a=p.parse_args();r=Path(a.repository_root).resolve()
 out=AutomaticShadowSignalPipeline().run(
  validation_result_path=r/"release/op2_09_to_op2_12/actual/multi_day_shadow_validation_result.json",
  pipeline_policy_path=r/"release/op2_13_to_op2_16/input/shadow_pipeline_policy.json",
  market_snapshot_path=r/"release/op2_13_to_op2_16/input/shadow_market_snapshot.json",
  strategy_snapshot_path=r/"release/op2_13_to_op2_16/input/shadow_strategy_snapshot.json",
  generated_signal_path=r/"release/op2_13_to_op2_16/actual/generated_shadow_signal.json",
  signal_queue_path=r/"release/op2_13_to_op2_16/actual/shadow_signal_queue.jsonl",
  validation_report_path=r/"release/op2_13_to_op2_16/actual/shadow_pipeline_validation_report.json",
  handoff_token_path=r/"release/op2_13_to_op2_16/actual/shadow_decision_handoff_token.json",
  result_path=r/"release/op2_13_to_op2_16/actual/automatic_shadow_signal_pipeline_result.json")
 print(json.dumps(out,indent=2,sort_keys=True));print("RESULT_FILE="+out["result_path"]);return 0 if out["status"]=="PASS" else 2
if __name__=="__main__":raise SystemExit(main())
