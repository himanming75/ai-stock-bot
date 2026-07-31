from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from tools.failure_injection_recovery_v77_9 import digest,load,summary
def verify_output(out:Path):
 r=load(out/"failure_injection_recovery_verification_v77_9.json");s=load(out/"failure_injection_recovery_summary_v77_9.json");e=[]
 if r.get("verification_sha256")!=digest({k:v for k,v in r.items() if k not in {"verification_sha256","issued_at_utc"}}):e.append("self-hash")
 if s!=summary(r):e.append("summary")
 fr=r.get("failure_report",{})
 for k,v in fr.get("checks",{}).items():
  if v is not True:e.append(k)
 for ok,n in ((r.get("status")=="PASS","status"),(fr.get("status")=="PASS","report"),
 (fr.get("blocked_failure_count")==4,"blocked"),(fr.get("detected_corruption_count")==4,"detected"),
 (r.get("verification_result",{}).get("failed_gate_count")==0,"gates"),
 (r.get("network_allowed") is False,"network"),(r.get("actual_orders_submitted")==0,"orders"),
 (r.get("next_phase")=="V77_10_RECOVERY_AUDIT_CERTIFICATE","next")):
  if not ok:e.append(n)
 return {"verified":not e,"status":"PASS" if not e else "FAIL","error_count":len(e),"errors":e,
 "failure_injection_recovery_sha256":r.get("failure_injection_recovery_sha256"),
 "recovered_state_sha256":fr.get("recovered_state_sha256"),
 "verification_sha256":r.get("verification_sha256"),"next_phase":r.get("next_phase")}
def main():
 p=argparse.ArgumentParser();p.add_argument("--output-dir",required=True);r=verify_output(Path(p.parse_args().output_dir));print(json.dumps(r,indent=2));return 0 if r["verified"] else 1
if __name__=="__main__":raise SystemExit(main())
