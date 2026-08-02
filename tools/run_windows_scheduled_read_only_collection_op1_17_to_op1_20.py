from pathlib import Path
import argparse,json,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from autonomous_paper_runtime.windows_scheduled_read_only_collection import WindowsScheduledReadOnlyCollection

def main():
 p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");a=p.parse_args();r=Path(a.repository_root).resolve()
 out=WindowsScheduledReadOnlyCollection().run(
  collector_result_path=r/"release/op1_13_to_op1_16/actual/automatic_snapshot_collector_result.json",
  schedule_policy_path=r/"release/op1_17_to_op1_20/input/windows_schedule_policy.json",
  recovery_snapshot_path=r/"release/op1_17_to_op1_20/input/scheduled_recovery_snapshot.json",
  task_plan_path=r/"release/op1_17_to_op1_20/actual/windows_task_plan.json",
  heartbeat_path=r/"release/op1_17_to_op1_20/actual/scheduled_collection_heartbeat.json",
  recovery_report_path=r/"release/op1_17_to_op1_20/actual/scheduled_recovery_report.json",
  schedule_token_path=r/"release/op1_17_to_op1_20/actual/windows_scheduled_collection_token.json",
  result_path=r/"release/op1_17_to_op1_20/actual/windows_scheduled_collection_result.json")
 print(json.dumps(out,indent=2,sort_keys=True));print("RESULT_FILE="+out["result_path"]);return 0 if out["status"]=="PASS" else 2
if __name__=="__main__":raise SystemExit(main())
