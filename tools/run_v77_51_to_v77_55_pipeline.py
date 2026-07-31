from pathlib import Path
import argparse,json,shutil,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from broker.paper_execution_pipeline_v77_51_55 import *
def main():
    p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");p.add_argument("--clean",action="store_true")
    a=p.parse_args();r=Path(a.repository_root).resolve()
    cert=r/"release/v77_50/output/backtest_audit_certificate_v77_50.json"
    sim=r/"release/v77_48/output/strategy_execution_simulation_v77_48.json"
    state=r/"release/v77_41/output/paper_portfolio_state_v77_41.json"
    if not all(x.is_file() for x in (cert,sim,state)):raise SystemExit("Missing V77.50/V77.48/V77.41 outputs.")
    out={v:r/f"release/v{v}/output" for v in ("77_51","77_52","77_53","77_54","77_55")}
    if a.clean:
        for x in out.values():shutil.rmtree(x,ignore_errors=True)
    s51=build_paper_order_intent(cert,sim,state,out["77_51"]);intent=out["77_51"]/"paper_order_intent_v77_51.json"
    s52=validate_paper_order(intent,state,out["77_52"]);val=out["77_52"]/"paper_order_validation_v77_52.json"
    s53=simulate_paper_fill(intent,val,out["77_53"]);fill=out["77_53"]/"paper_fill_simulation_v77_53.json"
    s54=run_paper_execution_safety_gate(intent,val,fill,out["77_54"])
    s55=issue_paper_execution_certificate(
      out["77_51"]/"paper_order_intent_verification_v77_51.json",
      out["77_52"]/"paper_order_validation_verification_v77_52.json",
      out["77_53"]/"paper_fill_simulation_verification_v77_53.json",
      out["77_54"]/"paper_execution_safety_gate_verification_v77_54.json",out["77_55"])
    stages=[s51,s52,s53,s54,s55]
    summary={"status":"PASS" if all(x.status=="PASS" for x in stages) else "FAIL","stage_count":5,
      "passed_stage_count":sum(x.status=="PASS" for x in stages),"failed_stage_count":sum(x.status!="PASS" for x in stages),
      "stages":[x.as_dict() for x in stages],**safety(),"next_phase":s55.next_phase}
    summary["pipeline_sha256"]=digest_json({k:v for k,v in summary.items() if k!="pipeline_sha256"})
    write_json(out["77_55"]/"paper_execution_pipeline_summary_v77_51_to_v77_55.json",summary)
    print(json.dumps(summary,indent=2));return 0 if summary["status"]=="PASS" else 1
if __name__=="__main__":raise SystemExit(main())
