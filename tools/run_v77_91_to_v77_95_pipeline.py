from pathlib import Path
import argparse,json,shutil,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from live_readiness.live_readiness_pipeline_v77_91_95 import *

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--repository-root",default=".")
    p.add_argument("--clean",action="store_true")
    a=p.parse_args()
    r=Path(a.repository_root).resolve()
    cert90=r/"release/v77_90/output/risk_stress_test_certificate_v77_90.json"
    cfg=r/"release/v77_91/config/live_readiness_config_v77_91.json"
    for f in (cert90,cfg):
        if not f.is_file():raise SystemExit(f"Missing required input: {f}")
    out={v:r/f"release/v{v}/output" for v in ("77_91","77_92","77_93","77_94","77_95")}
    if a.clean:
        for d in out.values():shutil.rmtree(d,ignore_errors=True)
    p91=build_live_readiness_audit_engine(cert90,cfg,out["77_91"])
    p92=build_operational_safety_checklist(out["77_91"]/"live_readiness_audit_engine_v77_91.json",out["77_92"])
    p93=run_recovery_kill_switch_audit(out["77_91"]/"live_readiness_audit_engine_v77_91.json",out["77_93"])
    p94=run_live_readiness_safety_gate(
        out["77_92"]/"operational_safety_checklist_v77_92.json",
        out["77_93"]/"recovery_kill_switch_audit_v77_93.json",
        out["77_91"]/"live_readiness_audit_engine_v77_91.json",
        out["77_94"])
    p95=issue_live_readiness_certificate(
        out["77_91"]/"live_readiness_audit_engine_verification_v77_91.json",
        out["77_92"]/"operational_safety_checklist_verification_v77_92.json",
        out["77_93"]/"recovery_kill_switch_audit_verification_v77_93.json",
        out["77_94"]/"live_readiness_safety_gate_verification_v77_94.json",
        out["77_91"]/"live_readiness_audit_engine_v77_91.json",
        out["77_95"])
    stages=[p91,p92,p93,p94,p95]
    champion=p95.get("champion_candidate") or {}
    summary={
        "status":"PASS" if all(x.get("status")=="PASS" for x in stages) else "FAIL",
        "stage_count":5,
        "passed_stage_count":sum(x.get("status")=="PASS" for x in stages),
        "failed_stage_count":sum(x.get("status")!="PASS" for x in stages),
        **safety(),
        "champion_candidate_id":champion.get("candidate_id"),
        "failed_stages":[{"stage":x.get("stage"),"errors":x.get("errors",[]),
                          "failed_checks":x.get("failed_checks",[]),
                          "failed_scenario_ids":x.get("failed_scenario_ids",[])}
                         for x in stages if x.get("status")!="PASS"],
        "next_phase":p95.get("next_phase")
    }
    summary["pipeline_sha256"]=digest_json({k:v for k,v in summary.items() if k!="pipeline_sha256"})
    write_json(out["77_95"]/"live_readiness_pipeline_summary_v77_91_to_v77_95.json",summary)
    print(json.dumps(summary,indent=2))
    return 0 if summary["status"]=="PASS" else 1

if __name__=="__main__":
    raise SystemExit(main())
