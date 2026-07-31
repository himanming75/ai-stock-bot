from pathlib import Path
import argparse,json,shutil,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from reporting.reporting_pipeline_v77_66_70 import *
def main():
 p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");p.add_argument("--clean",action="store_true")
 a=p.parse_args();r=Path(a.repository_root).resolve()
 perf=r/"release/v77_61/output/performance_analytics_v77_61.json"
 risk=r/"release/v77_63/output/risk_metrics_v77_63.json"
 cert=r/"release/v77_65/output/performance_audit_certificate_v77_65.json"
 for f in (perf,risk,cert):
  if not f.is_file():raise SystemExit(f"Missing required input: {f}")
 out={v:r/f"release/v{v}/output" for v in ("77_66","77_67","77_68","77_69","77_70")}
 if a.clean:
  for x in out.values():shutil.rmtree(x,ignore_errors=True)
 p66=build_report_generator(perf,risk,cert,out["77_66"])
 p67=build_equity_curve_visualization(perf,out["77_67"])
 p68=build_trade_statistics_dashboard(out["77_66"]/"performance_report_v77_66.json",risk,out["77_68"])
 p69=run_reporting_safety_gate(out["77_66"]/"performance_report_v77_66.json",
   out["77_67"]/"equity_curve_visualization_v77_67.json",
   out["77_68"]/"trade_statistics_dashboard_v77_68.json",out["77_69"])
 p70=issue_reporting_certificate(
   out["77_66"]/"performance_report_verification_v77_66.json",
   out["77_67"]/"equity_curve_visualization_verification_v77_67.json",
   out["77_68"]/"trade_statistics_dashboard_verification_v77_68.json",
   out["77_69"]/"reporting_safety_gate_verification_v77_69.json",out["77_70"])
 stages=[p66,p67,p68,p69,p70]
 summary={"status":"PASS" if all(x.get("status")=="PASS" for x in stages) else "FAIL","stage_count":5,
  "passed_stage_count":sum(x.get("status")=="PASS" for x in stages),
  "failed_stage_count":sum(x.get("status")!="PASS" for x in stages),**safety(),"next_phase":p70.get("next_phase")}
 summary["pipeline_sha256"]=digest_json({k:v for k,v in summary.items() if k!="pipeline_sha256"})
 write_json(out["77_70"]/"reporting_pipeline_summary_v77_66_to_v77_70.json",summary)
 print(json.dumps(summary,indent=2));return 0 if summary["status"]=="PASS" else 1
if __name__=="__main__":raise SystemExit(main())
