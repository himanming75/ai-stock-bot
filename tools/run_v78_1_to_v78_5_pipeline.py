from pathlib import Path
import argparse,json,shutil,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from paper_broker.paper_broker_pipeline_v78_1_5 import *

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--repository-root",default=".")
    p.add_argument("--clean",action="store_true")
    a=p.parse_args()
    r=Path(a.repository_root).resolve()
    cert100=r/"release/v77_100/output/broker_integration_skeleton_certificate_v77_100.json"
    cfg=r/"release/v78_1/config/paper_broker_config_v78_1.json"
    for f in (cert100,cfg):
        if not f.is_file():raise SystemExit(f"Missing required input: {f}")
    out={v:r/f"release/v{v}/output" for v in ("78_1","78_2","78_3","78_4","78_5")}
    if a.clean:
        for d in out.values():shutil.rmtree(d,ignore_errors=True)
    p1=build_paper_broker_foundation(cert100,cfg,out["78_1"])
    p2=run_paper_account_position_sync(out["78_1"]/"paper_broker_foundation_v78_1.json",out["78_2"])
    p3=run_paper_order_routing(out["78_1"]/"paper_broker_foundation_v78_1.json",out["78_3"])
    p4=run_paper_broker_safety_gate(
        out["78_1"]/"paper_broker_foundation_v78_1.json",
        out["78_2"]/"paper_account_position_sync_v78_2.json",
        out["78_3"]/"paper_order_routing_v78_3.json",
        out["78_4"])
    p5=issue_paper_broker_certificate(
        out["78_1"]/"paper_broker_foundation_verification_v78_1.json",
        out["78_2"]/"paper_account_position_sync_verification_v78_2.json",
        out["78_3"]/"paper_order_routing_verification_v78_3.json",
        out["78_4"]/"paper_broker_safety_gate_verification_v78_4.json",
        out["78_1"]/"paper_broker_foundation_v78_1.json",
        out["78_5"])
    stages=[p1,p2,p3,p4,p5]
    champion=p5.get("champion_candidate") or {}
    summary={
        "status":"PASS" if all(x.get("status")=="PASS" for x in stages) else "FAIL",
        "stage_count":5,
        "passed_stage_count":sum(x.get("status")=="PASS" for x in stages),
        "failed_stage_count":sum(x.get("status")!="PASS" for x in stages),
        **safety(),
        "champion_candidate_id":champion.get("candidate_id"),
        "failed_stages":[{"stage":x.get("stage"),"errors":x.get("errors",[]),
                          "failed_checks":x.get("failed_checks",[])}
                         for x in stages if x.get("status")!="PASS"],
        "next_phase":p5.get("next_phase")
    }
    summary["pipeline_sha256"]=digest_json({k:v for k,v in summary.items() if k!="pipeline_sha256"})
    write_json(out["78_5"]/"paper_broker_pipeline_summary_v78_1_to_v78_5.json",summary)
    print(json.dumps(summary,indent=2))
    return 0 if summary["status"]=="PASS" else 1

if __name__=="__main__":
    raise SystemExit(main())
