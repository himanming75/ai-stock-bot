from pathlib import Path
import argparse,json,shutil,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from fill_portfolio_bridge.fill_portfolio_bridge_pipeline_v78_61_65 import *

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--repository-root",default=".")
    p.add_argument("--clean",action="store_true")
    a=p.parse_args()
    r=Path(a.repository_root).resolve()

    cert=r/"release/v78_60/output/paper_broker_integration_certificate_v78_60.json"
    fills=r/"release/v78_58/output/paper_fill_simulation_engine_v78_58.json"
    cfg=r/"release/v78_61/config/fill_portfolio_bridge_config_v78_61.json"
    for f in (cert,fills,cfg):
        if not f.is_file():
            raise SystemExit(f"Missing required input: {f}")

    out={v:r/f"release/v{v}/output" for v in ("78_61","78_62","78_63","78_64","78_65")}
    if a.clean:
        for d in out.values():
            shutil.rmtree(d,ignore_errors=True)

    p61=build_fill_portfolio_bridge_foundation(cert,cfg,out["78_61"])
    p62=run_fill_normalization_portfolio_event(
        out["78_61"]/"fill_portfolio_bridge_foundation_v78_61.json",
        fills,out["78_62"])
    p63=run_fill_application_reconciliation(
        out["78_61"]/"fill_portfolio_bridge_foundation_v78_61.json",
        out["78_62"]/"fill_normalization_portfolio_event_v78_62.json",
        out["78_63"])
    p64=run_fill_portfolio_safety_gate(
        out["78_61"]/"fill_portfolio_bridge_foundation_v78_61.json",
        out["78_62"]/"fill_normalization_portfolio_event_v78_62.json",
        out["78_63"]/"fill_application_reconciliation_v78_63.json",
        out["78_64"])
    p65=issue_fill_portfolio_bridge_certificate(
        out["78_61"]/"fill_portfolio_bridge_foundation_verification_v78_61.json",
        out["78_62"]/"fill_normalization_portfolio_event_verification_v78_62.json",
        out["78_63"]/"fill_application_reconciliation_verification_v78_63.json",
        out["78_64"]/"fill_portfolio_safety_gate_verification_v78_64.json",
        out["78_61"]/"fill_portfolio_bridge_foundation_v78_61.json",
        out["78_65"])

    stages=[p61,p62,p63,p64,p65]
    champion=p65.get("champion_candidate") or {}
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
        "next_phase":p65.get("next_phase")
    }
    summary["pipeline_sha256"]=digest_json({k:v for k,v in summary.items() if k!="pipeline_sha256"})
    write_json(out["78_65"]/"fill_portfolio_bridge_pipeline_summary_v78_61_to_v78_65.json",summary)
    print(json.dumps(summary,indent=2))
    return 0 if summary["status"]=="PASS" else 1

if __name__=="__main__":
    raise SystemExit(main())
