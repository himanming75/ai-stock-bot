from pathlib import Path
import argparse,json,shutil,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from broker.portfolio_management_pipeline_v77_41_45 import *
def main():
    p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");p.add_argument("--clean",action="store_true")
    p.add_argument("--starting-cash",type=float,default=100000.0);a=p.parse_args()
    r=Path(a.repository_root).resolve()
    cert=r/"release/v77_40/output/risk_management_audit_certificate_v77_40.json"
    gate=r/"release/v77_39/output/risk_decision_safety_gate_v77_39.json"
    strategy=r/"release/v77_31/output/ai_strategy_input_v77_31.json"
    if not all(x.is_file() for x in (cert,gate,strategy)):raise SystemExit("Missing V77.40/V77.39/V77.31 outputs.")
    out={v:r/f"release/v{v}/output" for v in ("77_41","77_42","77_43","77_44","77_45")}
    if a.clean:
        for x in out.values():shutil.rmtree(x,ignore_errors=True)
    s41=build_paper_portfolio_state(cert,gate,strategy,out["77_41"],starting_cash=a.starting_cash)
    state=out["77_41"]/"paper_portfolio_state_v77_41.json"
    s42=build_position_ledger(state,out["77_42"])
    ledger=out["77_42"]/"portfolio_position_ledger_v77_42.json"
    s43=value_portfolio(state,ledger,out["77_43"])
    valuation=out["77_43"]/"portfolio_valuation_v77_43.json"
    s44=run_portfolio_safety_gate(state,ledger,valuation,out["77_44"])
    s45=issue_portfolio_certificate(
        out["77_41"]/"paper_portfolio_state_verification_v77_41.json",
        out["77_42"]/"portfolio_position_ledger_verification_v77_42.json",
        out["77_43"]/"portfolio_valuation_verification_v77_43.json",
        out["77_44"]/"portfolio_safety_gate_verification_v77_44.json",out["77_45"])
    stages=[s41,s42,s43,s44,s45]
    summary={"status":"PASS" if all(x.status=="PASS" for x in stages) else "FAIL","stage_count":5,
        "passed_stage_count":sum(x.status=="PASS" for x in stages),"failed_stage_count":sum(x.status!="PASS" for x in stages),
        "stages":[x.as_dict() for x in stages],**safety(),"next_phase":s45.next_phase}
    summary["pipeline_sha256"]=digest_json({k:v for k,v in summary.items() if k!="pipeline_sha256"})
    write_json(out["77_45"]/"portfolio_management_pipeline_summary_v77_41_to_v77_45.json",summary)
    print(json.dumps(summary,indent=2));return 0 if summary["status"]=="PASS" else 1
if __name__=="__main__":raise SystemExit(main())
