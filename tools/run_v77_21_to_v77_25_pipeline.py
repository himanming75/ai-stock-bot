from pathlib import Path
import argparse,json,shutil,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from broker.scheduled_runtime_pipeline_v77_21_25 import *
def main():
 p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");p.add_argument("--clean",action="store_true");p.add_argument("--run-count",type=int,default=5);p.add_argument("--interval-seconds",type=int,default=60);a=p.parse_args()
 r=Path(a.repository_root).resolve()
 cert=r/"release/v77_20/output/paper_runtime_audit_certificate_v77_20.json"
 if not cert.is_file():raise SystemExit("Missing V77.20 output certificate. Run V77.16-V77.20 pipeline first.")
 out={v:r/f"release/v{v}/output" for v in ("77_21","77_22","77_23","77_24","77_25")}
 if a.clean:
  for pth in out.values():shutil.rmtree(pth,ignore_errors=True)
 s21=build_scheduler(cert,out["77_21"],interval_seconds=a.interval_seconds,run_count=a.run_count)
 schedule=out["77_21"]/"paper_runtime_scheduler_v77_21.json"
 s22=build_execution_ledger(schedule,out["77_22"])
 ledger=out["77_22"]/"scheduled_session_execution_ledger_v77_22.json"
 s23=run_watchdog(ledger,out["77_23"])
 watchdog=out["77_23"]/"runtime_health_watchdog_v77_23.json"
 s24=auto_recover(watchdog,ledger,out["77_24"])
 s25=issue_scheduled_runtime_certificate(
  out["77_21"]/"paper_runtime_scheduler_verification_v77_21.json",
  out["77_22"]/"scheduled_session_execution_ledger_verification_v77_22.json",
  out["77_23"]/"runtime_health_watchdog_verification_v77_23.json",
  out["77_24"]/"runtime_failure_auto_recovery_verification_v77_24.json",
  out["77_25"])
 stages=[s21,s22,s23,s24,s25]
 summary={"status":"PASS" if all(x.status=="PASS" for x in stages) else "FAIL",
  "stage_count":5,"passed_stage_count":sum(x.status=="PASS" for x in stages),
  "failed_stage_count":sum(x.status!="PASS" for x in stages),
  "stages":[x.as_dict() for x in stages],**safety(),"next_phase":s25.next_phase}
 summary["pipeline_sha256"]=digest_json({k:v for k,v in summary.items() if k!="pipeline_sha256"})
 write_json(out["77_25"]/"scheduled_runtime_pipeline_summary_v77_21_to_v77_25.json",summary)
 print(json.dumps(summary,indent=2));return 0 if summary["status"]=="PASS" else 1
if __name__=="__main__":raise SystemExit(main())
