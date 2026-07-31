from pathlib import Path
import argparse,json,shutil,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from analytics.performance_analytics_pipeline_v77_61_65 import *
def main():
    p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");p.add_argument("--clean",action="store_true")
    a=p.parse_args();r=Path(a.repository_root).resolve()
    rec=r/"release/v77_56/output/portfolio_reconciliation_v77_56.json"
    if not rec.is_file():raise SystemExit("Missing V77.56 reconciliation output.")
    out={v:r/f"release/v{v}/output" for v in ("77_61","77_62","77_63","77_64","77_65")}
    if a.clean:
        for x in out.values():shutil.rmtree(x,ignore_errors=True)
    p61=build_performance_analytics(rec,out["77_61"])
    perf=out["77_61"]/"performance_analytics_v77_61.json"
    p62=build_return_attribution(perf,rec,out["77_62"])
    attr=out["77_62"]/"return_attribution_ledger_v77_62.json"
    p63=build_risk_metrics(perf,out["77_63"])
    risk=out["77_63"]/"risk_metrics_v77_63.json"
    p64=run_performance_safety_gate(perf,attr,risk,out["77_64"])
    p65=issue_performance_certificate(
      out["77_61"]/"performance_analytics_verification_v77_61.json",
      out["77_62"]/"return_attribution_ledger_verification_v77_62.json",
      out["77_63"]/"risk_metrics_verification_v77_63.json",
      out["77_64"]/"performance_safety_gate_verification_v77_64.json",out["77_65"])
    stages=[p61,p62,p63,p64,p65]
    summary={"status":"PASS" if all(x.get("status")=="PASS" for x in stages) else "FAIL",
      "stage_count":5,"passed_stage_count":sum(x.get("status")=="PASS" for x in stages),
      "failed_stage_count":sum(x.get("status")!="PASS" for x in stages),
      **safety(),"next_phase":p65.get("next_phase")}
    summary["pipeline_sha256"]=digest_json({k:v for k,v in summary.items() if k!="pipeline_sha256"})
    write_json(out["77_65"]/"performance_pipeline_summary_v77_61_to_v77_65.json",summary)
    print(json.dumps(summary,indent=2));return 0 if summary["status"]=="PASS" else 1
if __name__=="__main__":raise SystemExit(main())
