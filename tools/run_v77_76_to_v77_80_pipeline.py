from pathlib import Path
import argparse,json,shutil,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from walk_forward.walk_forward_pipeline_v77_76_80 import *

def main():
    p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");p.add_argument("--clean",action="store_true");a=p.parse_args()
    r=Path(a.repository_root).resolve()
    cert75=r/"release/v77_75/output/strategy_optimization_certificate_v77_75.json"
    cfg=r/"release/v77_76/config/walk_forward_config_v77_76.json"
    for f in (cert75,cfg):
        if not f.is_file():raise SystemExit(f"Missing required input: {f}")
    out={v:r/f"release/v{v}/output" for v in ("77_76","77_77","77_78","77_79","77_80")}
    if a.clean:
        for d in out.values():shutil.rmtree(d,ignore_errors=True)
    p76=build_walk_forward_engine(cert75,cfg,out["77_76"])
    p77=build_rolling_windows(out["77_76"]/"walk_forward_engine_v77_76.json",out["77_77"])
    p78=analyze_out_of_sample(out["77_76"]/"walk_forward_engine_v77_76.json",out["77_77"]/"rolling_windows_v77_77.json",out["77_78"])
    p79=run_walk_forward_safety_gate(out["77_78"]/"out_of_sample_analysis_v77_78.json",cfg,out["77_79"])
    p80=issue_walk_forward_certificate(
      out["77_76"]/"walk_forward_engine_verification_v77_76.json",
      out["77_77"]/"rolling_windows_verification_v77_77.json",
      out["77_78"]/"out_of_sample_analysis_verification_v77_78.json",
      out["77_79"]/"walk_forward_safety_gate_verification_v77_79.json",
      out["77_76"]/"walk_forward_engine_v77_76.json",
      out["77_78"]/"out_of_sample_analysis_v77_78.json",out["77_80"])
    stages=[p76,p77,p78,p79,p80];champion=p80.get("champion_candidate") or {}
    summary={"status":"PASS" if all(x.get("status")=="PASS" for x in stages) else "FAIL","stage_count":5,
      "passed_stage_count":sum(x.get("status")=="PASS" for x in stages),
      "failed_stage_count":sum(x.get("status")!="PASS" for x in stages),**safety(),
      "champion_candidate_id":champion.get("candidate_id"),
      "failed_stages":[{"stage":x.get("stage"),"errors":x.get("errors",[]),
                        "failed_checks":x.get("failed_checks",[])} for x in stages if x.get("status")!="PASS"],
      "next_phase":p80.get("next_phase")}
    summary["pipeline_sha256"]=digest_json({k:v for k,v in summary.items() if k!="pipeline_sha256"})
    write_json(out["77_80"]/"walk_forward_pipeline_summary_v77_76_to_v77_80.json",summary)
    print(json.dumps(summary,indent=2))
    return 0 if summary["status"]=="PASS" else 1
if __name__=="__main__":raise SystemExit(main())
