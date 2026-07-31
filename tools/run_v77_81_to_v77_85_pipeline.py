from pathlib import Path
import argparse,json,shutil,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from monte_carlo.monte_carlo_pipeline_v77_81_85 import *

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--repository-root",default=".")
    p.add_argument("--clean",action="store_true")
    a=p.parse_args()
    r=Path(a.repository_root).resolve()
    cert80=r/"release/v77_80/output/walk_forward_validation_certificate_v77_80.json"
    cfg=r/"release/v77_81/config/monte_carlo_config_v77_81.json"
    for f in (cert80,cfg):
        if not f.is_file():raise SystemExit(f"Missing required input: {f}")
    out={v:r/f"release/v{v}/output" for v in ("77_81","77_82","77_83","77_84","77_85")}
    if a.clean:
        for d in out.values():shutil.rmtree(d,ignore_errors=True)
    p81=build_monte_carlo_engine(cert80,cfg,out["77_81"])
    p82=run_randomized_execution_simulator(out["77_81"]/"monte_carlo_engine_v77_81.json",out["77_82"])
    p83=analyze_robustness_distribution(out["77_82"]/"randomized_execution_simulation_v77_82.json",out["77_83"])
    p84=run_monte_carlo_safety_gate(out["77_83"]/"robustness_distribution_v77_83.json",cfg,out["77_84"])
    p85=issue_monte_carlo_certificate(
        out["77_81"]/"monte_carlo_engine_verification_v77_81.json",
        out["77_82"]/"randomized_execution_simulation_verification_v77_82.json",
        out["77_83"]/"robustness_distribution_verification_v77_83.json",
        out["77_84"]/"monte_carlo_safety_gate_verification_v77_84.json",
        out["77_81"]/"monte_carlo_engine_v77_81.json",
        out["77_83"]/"robustness_distribution_v77_83.json",
        out["77_85"])
    stages=[p81,p82,p83,p84,p85]
    champion=p85.get("champion_candidate") or {}
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
        "next_phase":p85.get("next_phase")
    }
    summary["pipeline_sha256"]=digest_json({k:v for k,v in summary.items() if k!="pipeline_sha256"})
    write_json(out["77_85"]/"monte_carlo_pipeline_summary_v77_81_to_v77_85.json",summary)
    print(json.dumps(summary,indent=2))
    return 0 if summary["status"]=="PASS" else 1

if __name__=="__main__":
    raise SystemExit(main())
