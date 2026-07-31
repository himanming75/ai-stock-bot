from pathlib import Path
import argparse,json,shutil,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from reporting.reporting_pipeline_v78_76_80 import *

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--repository-root",default=".")
    p.add_argument("--clean",action="store_true")
    a=p.parse_args()
    r=Path(a.repository_root).resolve()

    cert=r/"release/v78_75/output/performance_accounting_certificate_v78_75.json"
    metrics=r/"release/v78_73/output/performance_metrics_engine_v78_73.json"
    equity=r/"release/v78_72/output/equity_curve_return_ledger_v78_72.json"
    cfg=r/"release/v78_76/config/reporting_config_v78_76.json"
    for f in (cert,metrics,equity,cfg):
        if not f.is_file():
            raise SystemExit(f"Missing required input: {f}")

    out={v:r/f"release/v{v}/output" for v in ("78_76","78_77","78_78","78_79","78_80")}
    if a.clean:
        for d in out.values():
            shutil.rmtree(d,ignore_errors=True)

    p76=build_reporting_foundation(cert,cfg,out["78_76"])
    p77=run_performance_report_builder(
        out["78_76"]/"reporting_foundation_v78_76.json",
        metrics,equity,out["78_77"])
    p78=run_report_export_engine(
        out["78_76"]/"reporting_foundation_v78_76.json",
        out["78_77"]/"performance_report_builder_v78_77.json",
        out["78_78"])
    p79=run_reporting_safety_gate(
        out["78_76"]/"reporting_foundation_v78_76.json",
        out["78_77"]/"performance_report_builder_v78_77.json",
        out["78_78"]/"report_export_engine_v78_78.json",
        out["78_79"])
    p80=issue_reporting_certificate(
        out["78_76"]/"reporting_foundation_verification_v78_76.json",
        out["78_77"]/"performance_report_builder_verification_v78_77.json",
        out["78_78"]/"report_export_engine_verification_v78_78.json",
        out["78_79"]/"reporting_safety_gate_verification_v78_79.json",
        out["78_76"]/"reporting_foundation_v78_76.json",
        out["78_80"])

    stages=[p76,p77,p78,p79,p80]
    champion=p80.get("champion_candidate") or {}
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
        "next_phase":p80.get("next_phase")
    }
    summary["pipeline_sha256"]=digest_json({k:v for k,v in summary.items() if k!="pipeline_sha256"})
    write_json(out["78_80"]/"reporting_pipeline_summary_v78_76_to_v78_80.json",summary)
    print(json.dumps(summary,indent=2))
    return 0 if summary["status"]=="PASS" else 1

if __name__=="__main__":
    raise SystemExit(main())
