from pathlib import Path
import argparse,json,shutil,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from runtime_scheduler.runtime_scheduler_pipeline_v78_21_25 import *
def main():
    p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");p.add_argument("--clean",action="store_true")
    a=p.parse_args();r=Path(a.repository_root).resolve()
    cert=r/"release/v78_20/output/session_manager_certificate_v78_20.json"
    cfg=r/"release/v78_21/config/runtime_scheduler_config_v78_21.json"
    for f in (cert,cfg):
        if not f.is_file():raise SystemExit(f"Missing required input: {f}")
    out={v:r/f"release/v{v}/output" for v in ("78_21","78_22","78_23","78_24","78_25")}
    if a.clean:
        for d in out.values():shutil.rmtree(d,ignore_errors=True)
    p21=build_runtime_scheduler_foundation(cert,cfg,out["78_21"])
    p22=build_scheduled_job_registry(out["78_21"]/"runtime_scheduler_foundation_v78_21.json",out["78_22"])
    p23=run_deterministic_tick_job_execution(out["78_21"]/"runtime_scheduler_foundation_v78_21.json",out["78_23"])
    p24=run_runtime_scheduler_safety_gate(
        out["78_21"]/"runtime_scheduler_foundation_v78_21.json",
        out["78_22"]/"scheduled_job_registry_v78_22.json",
        out["78_23"]/"deterministic_tick_job_execution_v78_23.json",out["78_24"])
    p25=issue_runtime_scheduler_certificate(
        out["78_21"]/"runtime_scheduler_foundation_verification_v78_21.json",
        out["78_22"]/"scheduled_job_registry_verification_v78_22.json",
        out["78_23"]/"deterministic_tick_job_execution_verification_v78_23.json",
        out["78_24"]/"runtime_scheduler_safety_gate_verification_v78_24.json",
        out["78_21"]/"runtime_scheduler_foundation_v78_21.json",out["78_25"])
    stages=[p21,p22,p23,p24,p25];champion=p25.get("champion_candidate") or {}
    summary={"status":"PASS" if all(x.get("status")=="PASS" for x in stages) else "FAIL",
      "stage_count":5,"passed_stage_count":sum(x.get("status")=="PASS" for x in stages),
      "failed_stage_count":sum(x.get("status")!="PASS" for x in stages),**safety(),
      "champion_candidate_id":champion.get("candidate_id"),
      "failed_stages":[{"stage":x.get("stage"),"errors":x.get("errors",[]),"failed_checks":x.get("failed_checks",[])}
                       for x in stages if x.get("status")!="PASS"],
      "next_phase":p25.get("next_phase")}
    summary["pipeline_sha256"]=digest_json({k:v for k,v in summary.items() if k!="pipeline_sha256"})
    write_json(out["78_25"]/"runtime_scheduler_pipeline_summary_v78_21_to_v78_25.json",summary)
    print(json.dumps(summary,indent=2));return 0 if summary["status"]=="PASS" else 1
if __name__=="__main__":raise SystemExit(main())
