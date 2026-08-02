from pathlib import Path
import argparse,json,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from autonomous_paper_runtime.autonomous_engine_bundle import AutonomousEngineBundle
def main():
 p=argparse.ArgumentParser(); p.add_argument("--repository-root",default="."); a=p.parse_args(); r=Path(a.repository_root).resolve()
 out=AutonomousEngineBundle().run(
 control_result_path=r/"release/v140_02_to_v140_05/actual/runtime_control_bundle_result.json",
 control_token_path=r/"release/v140_02_to_v140_05/actual/runtime_control_token.json",
 signal_path=r/"release/v140_06_to_v140_09/input/strategy_signal.json",
 account_path=r/"release/v140_06_to_v140_09/input/account_sizing_snapshot.json",
 recovery_path=r/"release/v140_06_to_v140_09/input/crash_recovery_snapshot.json",
 scheduler_path=r/"release/v140_06_to_v140_09/input/scheduler_snapshot.json",
 order_candidate_path=r/"release/v140_06_to_v140_09/actual/order_candidate.json",
 recovery_token_path=r/"release/v140_06_to_v140_09/actual/crash_recovery_token.json",
 heartbeat_path=r/"release/v140_06_to_v140_09/actual/scheduler_heartbeat.json",
 engine_token_path=r/"release/v140_06_to_v140_09/actual/autonomous_engine_token.json",
 result_path=r/"release/v140_06_to_v140_09/actual/autonomous_engine_bundle_result.json")
 print(json.dumps(out,indent=2,sort_keys=True)); print("RESULT_FILE="+out["result_path"]); return 0 if out["status"]=="PASS" else 2
if __name__=="__main__": raise SystemExit(main())
