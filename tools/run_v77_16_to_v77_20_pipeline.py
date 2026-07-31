from __future__ import annotations
from pathlib import Path
import argparse,json,shutil,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from broker.paper_runtime_pipeline_v77_16_20 import *
def main():
 p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");p.add_argument("--clean",action="store_true");p.add_argument("--cycles",type=int,default=1000);a=p.parse_args()
 r=Path(a.repository_root).resolve()
 cert=r/"release/v77_15/output/recovery_release_certificate_v77_15.json"
 if not cert.is_file():raise SystemExit("Missing V77.15 output certificate. Run V77.11-V77.15 pipeline first.")
 out={v:r/f"release/v{v}/output" for v in ("77_16","77_17","77_18","77_19","77_20")}
 if a.clean:
  for pth in out.values():shutil.rmtree(pth,ignore_errors=True)
 s16=build_session_orchestrator(cert,out["77_16"],session_id="PAPER-RUNTIME-V77-16")
 session=out["77_16"]/"paper_runtime_session_v77_16.json"
 s17=build_state_ledger(session,out["77_17"])
 ledger=out["77_17"]/"runtime_session_state_ledger_v77_17.json"
 s18=recover_session(session,ledger,out["77_18"])
 recovery=out["77_18"]/"automatic_restart_recovery_v77_18.json"
 s19=run_stability(recovery,out["77_19"],cycles=a.cycles)
 s20=issue_runtime_certificate(
  out["77_16"]/"paper_runtime_session_verification_v77_16.json",
  out["77_17"]/"runtime_session_state_ledger_verification_v77_17.json",
  out["77_18"]/"automatic_restart_recovery_verification_v77_18.json",
  out["77_19"]/"extended_paper_runtime_stability_verification_v77_19.json",
  out["77_20"])
 stages=[s16,s17,s18,s19,s20]
 summary={"status":"PASS" if all(x.status=="PASS" for x in stages) else "FAIL",
  "stage_count":5,"passed_stage_count":sum(x.status=="PASS" for x in stages),
  "failed_stage_count":sum(x.status!="PASS" for x in stages),
  "stages":[x.as_dict() for x in stages],**safety(),"next_phase":s20.next_phase}
 summary["pipeline_sha256"]=digest_json({k:v for k,v in summary.items() if k!="pipeline_sha256"})
 write_json(out["77_20"]/"paper_runtime_pipeline_summary_v77_16_to_v77_20.json",summary)
 print(json.dumps(summary,indent=2));return 0 if summary["status"]=="PASS" else 1
if __name__=="__main__":raise SystemExit(main())
