from pathlib import Path
import argparse,json,shutil,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from signal_risk_bridge.signal_risk_bridge_pipeline_v78_41_45 import *

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--repository-root",default=".")
    p.add_argument("--clean",action="store_true")
    a=p.parse_args()
    r=Path(a.repository_root).resolve()

    cert=r/"release/v78_40/output/strategy_runtime_certificate_v78_40.json"
    signals=r/"release/v78_38/output/deterministic_signal_execution_engine_v78_38.json"
    cfg=r/"release/v78_41/config/signal_risk_bridge_config_v78_41.json"
    for f in (cert,signals,cfg):
        if not f.is_file():
            raise SystemExit(f"Missing required input: {f}")

    out={v:r/f"release/v{v}/output" for v in ("78_41","78_42","78_43","78_44","78_45")}
    if a.clean:
        for d in out.values():
            shutil.rmtree(d,ignore_errors=True)

    p41=build_signal_risk_bridge_foundation(cert,cfg,out["78_41"])
    p42=run_signal_normalization_risk_request(
        out["78_41"]/"signal_risk_bridge_foundation_v78_41.json",
        signals,
        out["78_42"])
    p43=run_risk_decision_integration(
        out["78_41"]/"signal_risk_bridge_foundation_v78_41.json",
        out["78_42"]/"signal_normalization_risk_request_v78_42.json",
        out["78_43"])
    p44=run_signal_risk_safety_gate(
        out["78_41"]/"signal_risk_bridge_foundation_v78_41.json",
        out["78_42"]/"signal_normalization_risk_request_v78_42.json",
        out["78_43"]/"risk_decision_integration_v78_43.json",
        out["78_44"])
    p45=issue_signal_risk_bridge_certificate(
        out["78_41"]/"signal_risk_bridge_foundation_verification_v78_41.json",
        out["78_42"]/"signal_normalization_risk_request_verification_v78_42.json",
        out["78_43"]/"risk_decision_integration_verification_v78_43.json",
        out["78_44"]/"signal_risk_safety_gate_verification_v78_44.json",
        out["78_41"]/"signal_risk_bridge_foundation_v78_41.json",
        out["78_45"])

    stages=[p41,p42,p43,p44,p45]
    champion=p45.get("champion_candidate") or {}
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
        "next_phase":p45.get("next_phase")
    }
    summary["pipeline_sha256"]=digest_json({k:v for k,v in summary.items() if k!="pipeline_sha256"})
    write_json(out["78_45"]/"signal_risk_bridge_pipeline_summary_v78_41_to_v78_45.json",summary)
    print(json.dumps(summary,indent=2))
    return 0 if summary["status"]=="PASS" else 1

if __name__=="__main__":
    raise SystemExit(main())
