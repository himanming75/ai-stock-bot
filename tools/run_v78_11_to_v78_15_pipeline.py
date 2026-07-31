from pathlib import Path
import argparse,json,shutil,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from event_bus.event_bus_pipeline_v78_11_15 import *

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--repository-root",default=".")
    p.add_argument("--clean",action="store_true")
    a=p.parse_args()
    r=Path(a.repository_root).resolve()
    cert10=r/"release/v78_10/output/paper_event_certificate_v78_10.json"
    cfg=r/"release/v78_11/config/event_bus_config_v78_11.json"
    for f in (cert10,cfg):
        if not f.is_file():raise SystemExit(f"Missing required input: {f}")
    out={v:r/f"release/v{v}/output" for v in ("78_11","78_12","78_13","78_14","78_15")}
    if a.clean:
        for d in out.values():shutil.rmtree(d,ignore_errors=True)
    p11=build_event_bus_foundation(cert10,cfg,out["78_11"])
    p12=build_subscriber_registry(out["78_11"]/"event_bus_foundation_v78_11.json",out["78_12"])
    p13=run_event_dispatch_retry_dlq(out["78_11"]/"event_bus_foundation_v78_11.json",out["78_13"])
    p14=run_event_bus_safety_gate(
        out["78_11"]/"event_bus_foundation_v78_11.json",
        out["78_12"]/"subscriber_registry_v78_12.json",
        out["78_13"]/"event_dispatch_retry_dlq_v78_13.json",
        out["78_14"])
    p15=issue_event_bus_certificate(
        out["78_11"]/"event_bus_foundation_verification_v78_11.json",
        out["78_12"]/"subscriber_registry_verification_v78_12.json",
        out["78_13"]/"event_dispatch_retry_dlq_verification_v78_13.json",
        out["78_14"]/"event_bus_safety_gate_verification_v78_14.json",
        out["78_11"]/"event_bus_foundation_v78_11.json",
        out["78_15"])
    stages=[p11,p12,p13,p14,p15]
    champion=p15.get("champion_candidate") or {}
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
        "next_phase":p15.get("next_phase")
    }
    summary["pipeline_sha256"]=digest_json({k:v for k,v in summary.items() if k!="pipeline_sha256"})
    write_json(out["78_15"]/"event_bus_pipeline_summary_v78_11_to_v78_15.json",summary)
    print(json.dumps(summary,indent=2))
    return 0 if summary["status"]=="PASS" else 1

if __name__=="__main__":
    raise SystemExit(main())
