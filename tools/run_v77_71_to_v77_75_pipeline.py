from pathlib import Path
import argparse,json,shutil,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from optimization.strategy_optimization_pipeline_v77_71_75 import *
def main():
 p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");p.add_argument("--clean",action="store_true")
 a=p.parse_args();r=Path(a.repository_root).resolve()
 report=r/"release/v77_66/output/performance_report_v77_66.json"
 cert70=r/"release/v77_70/output/reporting_audit_certificate_v77_70.json"
 cfg=r/"release/v77_71/config/strategy_optimization_config_v77_71.json"
 for f in (report,cert70,cfg):
  if not f.is_file():raise SystemExit(f"Missing required input: {f}")
 out={v:r/f"release/v{v}/output" for v in ("77_71","77_72","77_73","77_74","77_75")}
 if a.clean:
  for d in out.values():shutil.rmtree(d,ignore_errors=True)
 p71=build_strategy_optimization_engine(report,cert70,cfg,out["77_71"])
 p72=run_grid_search(out["77_71"]/"strategy_optimization_engine_v77_71.json",out["77_72"])
 p73=rank_strategies(out["77_72"]/"grid_search_results_v77_72.json",
                     out["77_71"]/"strategy_optimization_engine_v77_71.json",out["77_73"])
 p74=run_optimization_safety_gate(out["77_73"]/"strategy_ranking_v77_73.json",cfg,out["77_74"])
 p75=issue_optimization_certificate(
   out["77_71"]/"strategy_optimization_engine_verification_v77_71.json",
   out["77_72"]/"grid_search_verification_v77_72.json",
   out["77_73"]/"strategy_ranking_verification_v77_73.json",
   out["77_74"]/"optimization_safety_gate_verification_v77_74.json",
   out["77_73"]/"strategy_ranking_v77_73.json",
   out["77_74"]/"optimization_safety_gate_v77_74.json",out["77_75"])
 stages=[p71,p72,p73,p74,p75]
 summary={"status":"PASS" if all(x.get("status")=="PASS" for x in stages) else "FAIL",
  "stage_count":5,"passed_stage_count":sum(x.get("status")=="PASS" for x in stages),
  "failed_stage_count":sum(x.get("status")!="PASS" for x in stages),
  **safety(),"champion_candidate_id":(p75.get("champion_candidate") or {}).get("candidate_id"),
  "failed_stages":[{"stage":x.get("stage"),"errors":x.get("errors",[])} for x in stages if x.get("status")!="PASS"],
  "next_phase":p75.get("next_phase")}
 summary["pipeline_sha256"]=digest_json({k:v for k,v in summary.items() if k!="pipeline_sha256"})
 write_json(out["77_75"]/"strategy_optimization_pipeline_summary_v77_71_to_v77_75.json",summary)
 print(json.dumps(summary,indent=2));return 0 if summary["status"]=="PASS" else 1
if __name__=="__main__":raise SystemExit(main())
