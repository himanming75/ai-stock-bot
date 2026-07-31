from pathlib import Path
import argparse,json,shutil,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from portfolio_runtime.portfolio_runtime_pipeline_v78_46_50 import *

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--repository-root",default=".")
    p.add_argument("--clean",action="store_true")
    a=p.parse_args()
    r=Path(a.repository_root).resolve()

    cert=r/"release/v78_45/output/signal_risk_bridge_certificate_v78_45.json"
    decisions=r/"release/v78_43/output/risk_decision_integration_v78_43.json"
    normalization=r/"release/v78_42/output/signal_normalization_risk_request_v78_42.json"
    cfg=r/"release/v78_46/config/portfolio_runtime_config_v78_46.json"

    for f in (cert,decisions,normalization,cfg):
        if not f.is_file():
            raise SystemExit(f"Missing required input: {f}")

    out={v:r/f"release/v{v}/output" for v in ("78_46","78_47","78_48","78_49","78_50")}
    if a.clean:
        for d in out.values():
            shutil.rmtree(d,ignore_errors=True)

    p46=build_portfolio_runtime_foundation(cert,cfg,out["78_46"])
    p47=build_portfolio_state_position_ledger(
        out["78_46"]/"portfolio_runtime_foundation_v78_46.json",
        decisions,normalization,out["78_47"])
    p48=run_approved_decision_application_engine(
        out["78_46"]/"portfolio_runtime_foundation_v78_46.json",
        out["78_48"])
    p49=run_portfolio_runtime_safety_gate(
        out["78_46"]/"portfolio_runtime_foundation_v78_46.json",
        out["78_47"]/"portfolio_state_position_ledger_v78_47.json",
        out["78_48"]/"approved_decision_application_engine_v78_48.json",
        out["78_49"])
    p50=issue_portfolio_runtime_certificate(
        out["78_46"]/"portfolio_runtime_foundation_verification_v78_46.json",
        out["78_47"]/"portfolio_state_position_ledger_verification_v78_47.json",
        out["78_48"]/"approved_decision_application_engine_verification_v78_48.json",
        out["78_49"]/"portfolio_runtime_safety_gate_verification_v78_49.json",
        out["78_46"]/"portfolio_runtime_foundation_v78_46.json",
        out["78_50"])

    stages=[p46,p47,p48,p49,p50]
    champion=p50.get("champion_candidate") or {}
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
        "next_phase":p50.get("next_phase")
    }
    summary["pipeline_sha256"]=digest_json({k:v for k,v in summary.items() if k!="pipeline_sha256"})
    write_json(out["78_50"]/"portfolio_runtime_pipeline_summary_v78_46_to_v78_50.json",summary)
    print(json.dumps(summary,indent=2))
    return 0 if summary["status"]=="PASS" else 1

if __name__=="__main__":
    raise SystemExit(main())
