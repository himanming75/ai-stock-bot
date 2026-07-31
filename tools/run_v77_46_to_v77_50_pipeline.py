from pathlib import Path
import argparse,json,shutil,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from broker.backtesting_integration_pipeline_v77_46_50 import *
def main():
 p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");p.add_argument("--clean",action="store_true");a=p.parse_args()
 r=Path(a.repository_root).resolve()
 cert=r/"release/v77_45/output/portfolio_audit_certificate_v77_45.json"
 strategy=r/"release/v77_31/output/ai_strategy_input_v77_31.json"
 state=r/"release/v77_41/output/paper_portfolio_state_v77_41.json"
 if not all(x.is_file() for x in (cert,strategy,state)):raise SystemExit("Missing V77.45/V77.31/V77.41 outputs.")
 out={v:r/f"release/v{v}/output" for v in ("77_46","77_47","77_48","77_49","77_50")}
 if a.clean:
  for x in out.values():shutil.rmtree(x,ignore_errors=True)
 s46=adapt_backtest_input(cert,strategy,state,out["77_46"]);inp=out["77_46"]/"backtest_input_adapter_v77_46.json"
 s47=replay_historical_data(inp,out["77_47"]);rep=out["77_47"]/"historical_data_replay_v77_47.json"
 s48=simulate_strategy_execution(rep,out["77_48"]);sim=out["77_48"]/"strategy_execution_simulation_v77_48.json"
 s49=run_backtest_safety_gate(inp,rep,sim,out["77_49"])
 s50=issue_backtest_certificate(out["77_46"]/"backtest_input_adapter_verification_v77_46.json",
   out["77_47"]/"historical_data_replay_verification_v77_47.json",
   out["77_48"]/"strategy_execution_simulation_verification_v77_48.json",
   out["77_49"]/"backtest_safety_gate_verification_v77_49.json",out["77_50"])
 stages=[s46,s47,s48,s49,s50]
 summary={"status":"PASS" if all(x.status=="PASS" for x in stages) else "FAIL","stage_count":5,
  "passed_stage_count":sum(x.status=="PASS" for x in stages),"failed_stage_count":sum(x.status!="PASS" for x in stages),
  "stages":[x.as_dict() for x in stages],**safety(),"next_phase":s50.next_phase}
 summary["pipeline_sha256"]=digest_json({k:v for k,v in summary.items() if k!="pipeline_sha256"})
 write_json(out["77_50"]/"backtesting_integration_pipeline_summary_v77_46_to_v77_50.json",summary)
 print(json.dumps(summary,indent=2));return 0 if summary["status"]=="PASS" else 1
if __name__=="__main__":raise SystemExit(main())
