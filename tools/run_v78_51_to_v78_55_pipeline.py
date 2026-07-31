from pathlib import Path
import argparse,json,shutil,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from execution_coordinator.execution_coordinator_pipeline_v78_51_55 import *

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--repository-root",default=".")
    p.add_argument("--clean",action="store_true")
    a=p.parse_args()
    r=Path(a.repository_root).resolve()

    cert=r/"release/v78_50/output/portfolio_runtime_certificate_v78_50.json"
    decisions=r/"release/v78_43/output/risk_decision_integration_v78_43.json"
    normalization=r/"release/v78_42/output/signal_normalization_risk_request_v78_42.json"
    cfg=r/"release/v78_51/config/execution_coordinator_config_v78_51.json"
    for f in (cert,decisions,normalization,cfg):
        if not f.is_file():
            raise SystemExit(f"Missing required input: {f}")

    out={v:r/f"release/v{v}/output" for v in ("78_51","78_52","78_53","78_54","78_55")}
    if a.clean:
        for d in out.values():
            shutil.rmtree(d,ignore_errors=True)

    p51=build_execution_coordinator_foundation(cert,cfg,out["78_51"])
    p52=run_approved_decision_to_order_intent(
        out["78_51"]/"execution_coordinator_foundation_v78_51.json",
        decisions,normalization,out["78_52"])
    p53=run_execution_queue_idempotency(
        out["78_52"]/"approved_decision_to_paper_order_intent_v78_52.json",
        out["78_53"])
    p54=run_execution_coordinator_safety_gate(
        out["78_51"]/"execution_coordinator_foundation_v78_51.json",
        out["78_52"]/"approved_decision_to_paper_order_intent_v78_52.json",
        out["78_53"]/"execution_queue_idempotency_v78_53.json",
        out["78_54"])
    p55=issue_execution_coordinator_certificate(
        out["78_51"]/"execution_coordinator_foundation_verification_v78_51.json",
        out["78_52"]/"approved_decision_to_paper_order_intent_verification_v78_52.json",
        out["78_53"]/"execution_queue_idempotency_verification_v78_53.json",
        out["78_54"]/"execution_coordinator_safety_gate_verification_v78_54.json",
        out["78_51"]/"execution_coordinator_foundation_v78_51.json",
        out["78_55"])

    stages=[p51,p52,p53,p54,p55]
    champion=p55.get("champion_candidate") or {}
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
        "next_phase":p55.get("next_phase")
    }
    summary["pipeline_sha256"]=digest_json({k:v for k,v in summary.items() if k!="pipeline_sha256"})
    write_json(out["78_55"]/"execution_coordinator_pipeline_summary_v78_51_to_v78_55.json",summary)
    print(json.dumps(summary,indent=2))
    return 0 if summary["status"]=="PASS" else 1

if __name__=="__main__":
    raise SystemExit(main())
