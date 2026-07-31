from pathlib import Path
import argparse,json,shutil,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from release_acceptance.release_acceptance_pipeline_v78_96_100 import *

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--repository-root",default=".")
    p.add_argument("--clean",action="store_true")
    a=p.parse_args()
    r=Path(a.repository_root).resolve()

    cert=r/"release/v78_95/output/final_system_certificate_v78_95.json"
    cfg=r/"release/v78_96/config/release_acceptance_config_v78_96.json"
    for f in (cert,cfg):
        if not f.is_file():
            raise SystemExit(f"Missing required input: {f}")

    out={v:r/f"release/v{v}/output" for v in ("78_96","78_97","78_98","78_99","78_100")}
    if a.clean:
        for d in out.values():
            shutil.rmtree(d,ignore_errors=True)

    p96=build_release_acceptance_foundation(cert,cfg,out["78_96"])
    p97=run_release_acceptance_checklist(
        r,out["78_96"]/"release_acceptance_foundation_v78_96.json",out["78_97"])
    p98=run_release_artifact_verification(
        r,
        out["78_96"]/"release_acceptance_foundation_v78_96.json",
        out["78_97"]/"release_acceptance_checklist_v78_97.json",
        out["78_98"])
    p99=run_release_acceptance_safety_gate(
        out["78_96"]/"release_acceptance_foundation_v78_96.json",
        out["78_97"]/"release_acceptance_checklist_v78_97.json",
        out["78_98"]/"release_artifact_verification_v78_98.json",
        out["78_99"])
    p100=issue_final_release_certificate(
        out["78_96"]/"release_acceptance_foundation_verification_v78_96.json",
        out["78_97"]/"release_acceptance_checklist_verification_v78_97.json",
        out["78_98"]/"release_artifact_verification_verification_v78_98.json",
        out["78_99"]/"release_acceptance_safety_gate_verification_v78_99.json",
        out["78_96"]/"release_acceptance_foundation_v78_96.json",
        out["78_98"]/"release_artifact_verification_v78_98.json",
        out["78_100"])

    stages=[p96,p97,p98,p99,p100]
    champion=p100.get("champion_candidate") or {}
    summary={
        "status":"PASS" if all(x.get("status")=="PASS" for x in stages) else "FAIL",
        "stage_count":5,
        "passed_stage_count":sum(x.get("status")=="PASS" for x in stages),
        "failed_stage_count":sum(x.get("status")!="PASS" for x in stages),
        **safety(),
        "release_ready":p100.get("release_ready"),
        "release_name":p100.get("release_name"),
        "release_version":p100.get("release_version"),
        "system_id":p100.get("system_id"),
        "system_version":p100.get("system_version"),
        "release_id":p100.get("release_id"),
        "runtime_id":p100.get("runtime_id"),
        "champion_candidate_id":champion.get("candidate_id"),
        "module_chain_head":p100.get("module_chain_head"),
        "artifact_chain_head":p100.get("artifact_chain_head"),
        "final_release_manifest_sha256":p100.get("final_release_manifest_sha256"),
        "failed_stages":[
            {"stage":x.get("stage"),"errors":x.get("errors",[]),"failed_checks":x.get("failed_checks",[])}
            for x in stages if x.get("status")!="PASS"
        ],
        "next_phase":p100.get("next_phase")
    }
    summary["pipeline_sha256"]=digest_json({k:v for k,v in summary.items() if k!="pipeline_sha256"})
    write_json(out["78_100"]/"release_acceptance_pipeline_summary_v78_96_to_v78_100.json",summary)
    print(json.dumps(summary,indent=2))
    return 0 if summary["status"]=="PASS" else 1

if __name__=="__main__":
    raise SystemExit(main())
