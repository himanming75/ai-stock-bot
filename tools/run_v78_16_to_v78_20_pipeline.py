from pathlib import Path
import argparse,json,shutil,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from paper_session.paper_session_pipeline_v78_16_20 import *
def main():
    p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");p.add_argument("--clean",action="store_true")
    a=p.parse_args();r=Path(a.repository_root).resolve()
    cert=r/"release/v78_15/output/event_bus_certificate_v78_15.json"
    cfg=r/"release/v78_16/config/paper_session_config_v78_16.json"
    for f in (cert,cfg):
        if not f.is_file():raise SystemExit(f"Missing required input: {f}")
    out={v:r/f"release/v{v}/output" for v in ("78_16","78_17","78_18","78_19","78_20")}
    if a.clean:
        for d in out.values():shutil.rmtree(d,ignore_errors=True)
    p16=build_session_manager_foundation(cert,cfg,out["78_16"])
    p17=run_session_lifecycle(out["78_16"]/"paper_session_manager_foundation_v78_16.json",out["78_17"])
    p18=run_checkpoint_resume(out["78_16"]/"paper_session_manager_foundation_v78_16.json",out["78_18"])
    p19=run_session_manager_safety_gate(
        out["78_16"]/"paper_session_manager_foundation_v78_16.json",
        out["78_17"]/"session_lifecycle_state_machine_v78_17.json",
        out["78_18"]/"session_checkpoint_resume_v78_18.json",out["78_19"])
    p20=issue_session_manager_certificate(
        out["78_16"]/"paper_session_manager_foundation_verification_v78_16.json",
        out["78_17"]/"session_lifecycle_state_machine_verification_v78_17.json",
        out["78_18"]/"session_checkpoint_resume_verification_v78_18.json",
        out["78_19"]/"session_manager_safety_gate_verification_v78_19.json",
        out["78_16"]/"paper_session_manager_foundation_v78_16.json",out["78_20"])
    stages=[p16,p17,p18,p19,p20];champion=p20.get("champion_candidate") or {}
    summary={"status":"PASS" if all(x.get("status")=="PASS" for x in stages) else "FAIL",
      "stage_count":5,"passed_stage_count":sum(x.get("status")=="PASS" for x in stages),
      "failed_stage_count":sum(x.get("status")!="PASS" for x in stages),**safety(),
      "champion_candidate_id":champion.get("candidate_id"),
      "failed_stages":[{"stage":x.get("stage"),"errors":x.get("errors",[]),"failed_checks":x.get("failed_checks",[])}
                       for x in stages if x.get("status")!="PASS"],
      "next_phase":p20.get("next_phase")}
    summary["pipeline_sha256"]=digest_json({k:v for k,v in summary.items() if k!="pipeline_sha256"})
    write_json(out["78_20"]/"paper_session_pipeline_summary_v78_16_to_v78_20.json",summary)
    print(json.dumps(summary,indent=2));return 0 if summary["status"]=="PASS" else 1
if __name__=="__main__":raise SystemExit(main())
