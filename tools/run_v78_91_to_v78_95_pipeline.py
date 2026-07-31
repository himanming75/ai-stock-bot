from pathlib import Path
import argparse,json,shutil,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from final_system_certification.final_system_certification_pipeline_v78_91_95 import *

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--repository-root",default=".")
    p.add_argument("--clean",action="store_true")
    a=p.parse_args()
    r=Path(a.repository_root).resolve()

    runtime_cert=r/"release/v78_90/output/operation_runtime_certificate_v78_90.json"
    cfg=r/"release/v78_91/config/final_system_certification_config_v78_91.json"
    for f in (runtime_cert,cfg):
        if not f.is_file():
            raise SystemExit(f"Missing required input: {f}")

    out={v:r/f"release/v{v}/output" for v in ("78_91","78_92","78_93","78_94","78_95")}
    if a.clean:
        for d in out.values():
            shutil.rmtree(d,ignore_errors=True)

    p91=build_final_system_certification_foundation(runtime_cert,cfg,out["78_91"])
    p92=run_cross_module_integrity_audit(
        r,out["78_91"]/"final_system_certification_foundation_v78_91.json",out["78_92"])
    p93=run_end_to_end_replay_validation(
        r,
        out["78_91"]/"final_system_certification_foundation_v78_91.json",
        out["78_92"]/"cross_module_integrity_audit_v78_92.json",
        out["78_93"])
    p94=run_final_system_safety_gate(
        out["78_91"]/"final_system_certification_foundation_v78_91.json",
        out["78_92"]/"cross_module_integrity_audit_v78_92.json",
        out["78_93"]/"end_to_end_replay_validation_v78_93.json",
        out["78_94"])
    p95=issue_final_system_certificate(
        out["78_91"]/"final_system_certification_foundation_verification_v78_91.json",
        out["78_92"]/"cross_module_integrity_audit_verification_v78_92.json",
        out["78_93"]/"end_to_end_replay_validation_verification_v78_93.json",
        out["78_94"]/"final_system_safety_gate_verification_v78_94.json",
        out["78_91"]/"final_system_certification_foundation_v78_91.json",
        out["78_92"]/"cross_module_integrity_audit_v78_92.json",
        out["78_95"])

    stages=[p91,p92,p93,p94,p95]
    champion=p95.get("champion_candidate") or {}
    summary={
        "status":"PASS" if all(x.get("status")=="PASS" for x in stages) else "FAIL",
        "stage_count":5,
        "passed_stage_count":sum(x.get("status")=="PASS" for x in stages),
        "failed_stage_count":sum(x.get("status")!="PASS" for x in stages),
        **safety(),
        "champion_candidate_id":champion.get("candidate_id"),
        "system_id":p95.get("system_id"),
        "system_version":p95.get("system_version"),
        "release_id":p95.get("release_id"),
        "runtime_id":p95.get("runtime_id"),
        "module_chain_head":p95.get("module_chain_head"),
        "failed_stages":[
            {"stage":x.get("stage"),"errors":x.get("errors",[]),"failed_checks":x.get("failed_checks",[])}
            for x in stages if x.get("status")!="PASS"
        ],
        "next_phase":p95.get("next_phase")
    }
    summary["pipeline_sha256"]=digest_json({k:v for k,v in summary.items() if k!="pipeline_sha256"})
    write_json(out["78_95"]/"final_system_certification_pipeline_summary_v78_91_to_v78_95.json",summary)
    print(json.dumps(summary,indent=2))
    return 0 if summary["status"]=="PASS" else 1

if __name__=="__main__":
    raise SystemExit(main())
