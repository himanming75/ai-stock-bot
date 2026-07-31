from pathlib import Path
import argparse,json,shutil,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from deployment.deployment_pipeline_v78_81_85 import *

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--repository-root",default=".")
    p.add_argument("--clean",action="store_true")
    a=p.parse_args()
    r=Path(a.repository_root).resolve()

    cert=r/"release/v78_80/output/reporting_certificate_v78_80.json"
    cfg=r/"release/v78_81/config/deployment_config_v78_81.json"
    for f in (cert,cfg):
        if not f.is_file():
            raise SystemExit(f"Missing required input: {f}")

    out={v:r/f"release/v{v}/output" for v in ("78_81","78_82","78_83","78_84","78_85")}
    if a.clean:
        for d in out.values():
            shutil.rmtree(d,ignore_errors=True)

    p81=build_deployment_foundation(cert,cfg,out["78_81"])
    p82=run_deployment_package_builder(
        r,out["78_81"]/"deployment_foundation_v78_81.json",out["78_82"])
    p83=run_deployment_validation(
        r,
        out["78_81"]/"deployment_foundation_v78_81.json",
        out["78_82"]/"deployment_package_builder_v78_82.json",
        out["78_83"])
    p84=run_deployment_safety_gate(
        out["78_81"]/"deployment_foundation_v78_81.json",
        out["78_82"]/"deployment_package_builder_v78_82.json",
        out["78_83"]/"deployment_validation_v78_83.json",
        out["78_84"])
    p85=issue_deployment_certificate(
        out["78_81"]/"deployment_foundation_verification_v78_81.json",
        out["78_82"]/"deployment_package_builder_verification_v78_82.json",
        out["78_83"]/"deployment_validation_verification_v78_83.json",
        out["78_84"]/"deployment_safety_gate_verification_v78_84.json",
        out["78_81"]/"deployment_foundation_v78_81.json",
        out["78_82"]/"deployment_package_builder_v78_82.json",
        out["78_85"])

    stages=[p81,p82,p83,p84,p85]
    champion=p85.get("champion_candidate") or {}
    summary={
        "status":"PASS" if all(x.get("status")=="PASS" for x in stages) else "FAIL",
        "stage_count":5,
        "passed_stage_count":sum(x.get("status")=="PASS" for x in stages),
        "failed_stage_count":sum(x.get("status")!="PASS" for x in stages),
        **safety(),
        "champion_candidate_id":champion.get("candidate_id"),
        "release_id":p85.get("release_id"),
        "manifest_sha256":p85.get("manifest_sha256"),
        "failed_stages":[
            {"stage":x.get("stage"),"errors":x.get("errors",[]),"failed_checks":x.get("failed_checks",[])}
            for x in stages if x.get("status")!="PASS"
        ],
        "next_phase":p85.get("next_phase")
    }
    summary["pipeline_sha256"]=digest_json({k:v for k,v in summary.items() if k!="pipeline_sha256"})
    write_json(out["78_85"]/"deployment_pipeline_summary_v78_81_to_v78_85.json",summary)
    print(json.dumps(summary,indent=2))
    return 0 if summary["status"]=="PASS" else 1

if __name__=="__main__":
    raise SystemExit(main())
