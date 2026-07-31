from pathlib import Path
import argparse,json,shutil,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from performance_accounting.performance_accounting_pipeline_v78_71_75 import *

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--repository-root",default=".")
    p.add_argument("--clean",action="store_true")
    a=p.parse_args()
    r=Path(a.repository_root).resolve()

    cert=r/"release/v78_70/output/audit_reconciliation_certificate_v78_70.json"
    cfg=r/"release/v78_71/config/performance_accounting_config_v78_71.json"
    for f in (cert,cfg):
        if not f.is_file():
            raise SystemExit(f"Missing required input: {f}")

    out={v:r/f"release/v{v}/output" for v in ("78_71","78_72","78_73","78_74","78_75")}
    if a.clean:
        for d in out.values():
            shutil.rmtree(d,ignore_errors=True)

    p71=build_performance_accounting_foundation(cert,cfg,out["78_71"])
    p72=run_equity_curve_return_ledger(
        out["78_71"]/"performance_accounting_foundation_v78_71.json",
        out["78_72"])
    p73=run_performance_metrics_engine(
        out["78_71"]/"performance_accounting_foundation_v78_71.json",
        out["78_72"]/"equity_curve_return_ledger_v78_72.json",
        out["78_73"])
    p74=run_performance_accounting_safety_gate(
        out["78_71"]/"performance_accounting_foundation_v78_71.json",
        out["78_72"]/"equity_curve_return_ledger_v78_72.json",
        out["78_73"]/"performance_metrics_engine_v78_73.json",
        out["78_74"])
    p75=issue_performance_accounting_certificate(
        out["78_71"]/"performance_accounting_foundation_verification_v78_71.json",
        out["78_72"]/"equity_curve_return_ledger_verification_v78_72.json",
        out["78_73"]/"performance_metrics_engine_verification_v78_73.json",
        out["78_74"]/"performance_accounting_safety_gate_verification_v78_74.json",
        out["78_71"]/"performance_accounting_foundation_v78_71.json",
        out["78_75"])

    stages=[p71,p72,p73,p74,p75]
    champion=p75.get("champion_candidate") or {}
    summary={
        "status":"PASS" if all(x.get("status")=="PASS" for x in stages) else "FAIL",
        "stage_count":5,
        "passed_stage_count":sum(x.get("status")=="PASS" for x in stages),
        "failed_stage_count":sum(x.get("status")!="PASS" for x in stages),
        **safety(),
        "champion_candidate_id":champion.get("candidate_id"),
        "failed_stages":[
            {"stage":x.get("stage"),"errors":x.get("errors",[]),"failed_checks":x.get("failed_checks",[])}
            for x in stages if x.get("status")!="PASS"
        ],
        "next_phase":p75.get("next_phase")
    }
    summary["pipeline_sha256"]=digest_json({k:v for k,v in summary.items() if k!="pipeline_sha256"})
    write_json(out["78_75"]/"performance_accounting_pipeline_summary_v78_71_to_v78_75.json",summary)
    print(json.dumps(summary,indent=2))
    return 0 if summary["status"]=="PASS" else 1

if __name__=="__main__":
    raise SystemExit(main())
