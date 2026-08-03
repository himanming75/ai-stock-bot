from pathlib import Path
import argparse,json,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from paper_pilot.paper_trading_completion import PaperTradingCompletionPackage

def main():
 a=argparse.ArgumentParser();a.add_argument('--repository-root',default='.');args=a.parse_args();r=Path(args.repository_root).resolve()
 result=PaperTradingCompletionPackage().run(policy_path=r/'release/v80_01_to_v80_04/input/paper_trading_completion_policy.json',pilot_result_path=r/'release/op4_01_to_op4_04/actual/controlled_paper_pilot_foundation_result.json',session_result_path=r/'release/op4_05_to_op4_08/actual/paper_session_monitor_result.json',performance_result_path=r/'release/op4_09_to_op4_12/actual/paper_performance_collector_result.json',risk_result_path=r/'release/op4_13_to_op4_16/actual/paper_risk_monitor_result.json',automation_result_path=r/'release/op4_17_to_op4_20/actual/paper_pilot_automation_result.json',validation_result_path=r/'release/op5_01_to_op5_04/actual/multi_day_validation_result.json',analytics_result_path=r/'release/op5_05_to_op5_08/actual/validation_analytics_result.json',certificate_result_path=r/'release/op5_09_to_op5_12/actual/validation_certificate_result.json',promotion_result_path=r/'release/op5_13_to_op5_16/actual/promotion_gate_result.json',approval_result_path=r/'release/op5_17_to_op5_20/actual/promotion_approval_result.json',completion_manifest_path=r/'release/v80_01_to_v80_04/actual/paper_trading_completion_manifest.json',integrity_manifest_path=r/'release/v80_01_to_v80_04/actual/paper_trading_completion_integrity.json',dashboard_state_path=r/'release/v80_01_to_v80_04/actual/paper_trading_completion_dashboard_state.json',result_path=r/'release/v80_01_to_v80_04/actual/paper_trading_completion_result.json')
 print(json.dumps(result,indent=2,sort_keys=True));print('RESULT_FILE='+result['result_path']);return 0 if result['status']=='PASS' else 2
if __name__=='__main__':raise SystemExit(main())
