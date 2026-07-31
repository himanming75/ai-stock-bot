from pathlib import Path
import argparse,json,shutil,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from operation_runtime.operation_runtime_pipeline_v78_86_90 import *

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--repository-root",default=".")
    p.add_argument("--clean",action="store_true")
    a=p.parse_args()
    r=Path(a.repository_root).resolve()

    cert=r/"release/v78_85/output/deployment_certificate_v78_85.json"
    cfg=r/"release/v78_86/config/operation_runtime_config_v78_86.json"
    for f in (cert,cfg):
        if not f.is_file():
            raise SystemExit(f"Missing required input: {f}")

    out={v:r/f"release/v{v}/output" for v in ("78_86","78_87","78_88","78_89","78_90")}
    if a.clean:
        for d in out.values():
            shutil.rmtree(d,ignore_errors=True)

    p86=build_operation_runtime_foundation(cert,cfg,out["78_86"])
    p87=run_runtime_health_heartbeat(
        out["78_86"]/"operation_runtime_foundation_v78_86.json",
        out["78_87"])
    p88=run_runtime_recovery_restart(
        out["78_86"]/"operation_runtime_foundation_v78_86.json",
        out["78_87"]/"runtime_health_heartbeat_v78_87.json",
        out["78_88"])
    p89=run_operation_runtime_safety_gate(
        out["78_86"]/"operation_runtime_foundation_v78_86.json",
        out["78_87"]/"runtime_health_heartbeat_v78_87.json",
        out["78_88"]/"runtime_recovery_restart_v78_88.json",
        out["78_89"])
    p90=issue_operation_runtime_certificate(
        out["78_86"]/"operation_runtime_foundation_verification_v78_86.json",
        out["78_87"]/"runtime_health_heartbeat_verification_v78_87.json",
        out["78_88"]/"runtime_recovery_restart_verification_v78_88.json",
        out["78_89"]/"operation_runtime_safety_gate_verification_v78_89.json",
        out["78_86"]/"operation_runtime_foundation_v78_86.json",
        out["78_90"])

    stages=[p86,p87,p88,p89,p90]
    champion=p90.get("champion_candidate") or {}
    summary={
        "status":"PASS" if all(x.get("status")=="PASS" for x in stages) else "FAIL",
        "stage_count":5,
        "passed_stage_count":sum(x.get("status")=="PASS" for x in stages),
        "failed_stage_count":sum(x.get("status")!="PASS" for x in stages),
        **safety(),
        "champion_candidate_id":champion.get("candidate_id"),
        "runtime_id":p90.get("runtime_id"),
        "release_id":p90.get("release_id"),
        "failed_stages":[
            {"stage":x.get("stage"),"errors":x.get("errors",[]),"failed_checks":x.get("failed_checks",[])}
            for x in stages if x.get("status")!="PASS"
        ],
        "next_phase":p90.get("next_phase")
    }
    summary["pipeline_sha256"]=digest_json({k:v for k,v in summary.items() if k!="pipeline_sha256"})
    write_json(out["78_90"]/"operation_runtime_pipeline_summary_v78_86_to_v78_90.json",summary)
    print(json.dumps(summary,indent=2))
    return 0 if summary["status"]=="PASS" else 1

if __name__=="__main__":
    raise SystemExit(main())
