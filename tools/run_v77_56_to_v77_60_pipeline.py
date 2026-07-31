from pathlib import Path
import argparse,json,shutil,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from broker.portfolio_reconciliation_pipeline_v77_56_60 import *
def main():
    p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");p.add_argument("--clean",action="store_true")
    a=p.parse_args();r=Path(a.repository_root).resolve()
    state=r/"release/v77_41/output/paper_portfolio_state_v77_41.json"
    fill=r/"release/v77_53/output/paper_fill_simulation_v77_53.json"
    cert=r/"release/v77_55/output/paper_execution_audit_certificate_v77_55.json"
    if not all(x.is_file() for x in (state,fill,cert)):raise SystemExit("Missing V77.41/V77.53/V77.55 outputs.")
    out={v:r/f"release/v{v}/output" for v in ("77_56","77_57","77_58","77_59","77_60")}
    if a.clean:
        for x in out.values():shutil.rmtree(x,ignore_errors=True)
    s56=reconcile_portfolio(state,fill,cert,out["77_56"]);rec=out["77_56"]/"portfolio_reconciliation_v77_56.json"
    s57=build_cash_reconciliation_ledger(rec,out["77_57"]);cash=out["77_57"]/"cash_reconciliation_ledger_v77_57.json"
    s58=build_position_reconciliation_ledger(state,rec,out["77_58"]);pos=out["77_58"]/"position_reconciliation_ledger_v77_58.json"
    s59=run_reconciliation_safety_gate(rec,cash,pos,out["77_59"])
    s60=issue_reconciliation_certificate(
      out["77_56"]/"portfolio_reconciliation_verification_v77_56.json",
      out["77_57"]/"cash_reconciliation_ledger_verification_v77_57.json",
      out["77_58"]/"position_reconciliation_ledger_verification_v77_58.json",
      out["77_59"]/"reconciliation_safety_gate_verification_v77_59.json",out["77_60"])
    stages=[s56,s57,s58,s59,s60]
    summary={"status":"PASS" if all(x.status=="PASS" for x in stages) else "FAIL","stage_count":5,
      "passed_stage_count":sum(x.status=="PASS" for x in stages),"failed_stage_count":sum(x.status!="PASS" for x in stages),
      "stages":[x.as_dict() for x in stages],**safety(),"next_phase":s60.next_phase}
    summary["pipeline_sha256"]=digest_json({k:v for k,v in summary.items() if k!="pipeline_sha256"})
    write_json(out["77_60"]/"portfolio_reconciliation_pipeline_summary_v77_56_to_v77_60.json",summary)
    print(json.dumps(summary,indent=2));return 0 if summary["status"]=="PASS" else 1
if __name__=="__main__":raise SystemExit(main())
