from pathlib import Path
import argparse,json,shutil,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from paper_broker_integration.paper_broker_integration_pipeline_v78_56_60 import *

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--repository-root",default=".")
    p.add_argument("--clean",action="store_true")
    a=p.parse_args()
    r=Path(a.repository_root).resolve()

    cert=r/"release/v78_55/output/execution_coordinator_certificate_v78_55.json"
    intents=r/"release/v78_52/output/approved_decision_to_paper_order_intent_v78_52.json"
    cfg=r/"release/v78_56/config/paper_broker_integration_config_v78_56.json"
    for f in (cert,intents,cfg):
        if not f.is_file():
            raise SystemExit(f"Missing required input: {f}")

    out={v:r/f"release/v{v}/output" for v in ("78_56","78_57","78_58","78_59","78_60")}
    if a.clean:
        for d in out.values():
            shutil.rmtree(d,ignore_errors=True)

    p56=build_paper_broker_integration_foundation(cert,cfg,out["78_56"])
    p57=run_paper_order_submission_pipeline(
        out["78_56"]/"paper_broker_integration_foundation_v78_56.json",
        intents,out["78_57"])
    p58=run_paper_fill_simulation(
        out["78_56"]/"paper_broker_integration_foundation_v78_56.json",
        out["78_57"]/"paper_order_submission_pipeline_v78_57.json",
        out["78_58"])
    p59=run_paper_broker_integration_safety_gate(
        out["78_56"]/"paper_broker_integration_foundation_v78_56.json",
        out["78_57"]/"paper_order_submission_pipeline_v78_57.json",
        out["78_58"]/"paper_fill_simulation_engine_v78_58.json",
        out["78_59"])
    p60=issue_paper_broker_integration_certificate(
        out["78_56"]/"paper_broker_integration_foundation_verification_v78_56.json",
        out["78_57"]/"paper_order_submission_pipeline_verification_v78_57.json",
        out["78_58"]/"paper_fill_simulation_engine_verification_v78_58.json",
        out["78_59"]/"paper_broker_integration_safety_gate_verification_v78_59.json",
        out["78_56"]/"paper_broker_integration_foundation_v78_56.json",
        out["78_60"])

    stages=[p56,p57,p58,p59,p60]
    champion=p60.get("champion_candidate") or {}
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
        "next_phase":p60.get("next_phase")
    }
    summary["pipeline_sha256"]=digest_json({k:v for k,v in summary.items() if k!="pipeline_sha256"})
    write_json(out["78_60"]/"paper_broker_integration_pipeline_summary_v78_56_to_v78_60.json",summary)
    print(json.dumps(summary,indent=2))
    return 0 if summary["status"]=="PASS" else 1

if __name__=="__main__":
    raise SystemExit(main())
