from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from broker.recovery_audit_certificate_v77_10 import RecoveryAuditCertificateBuilder,RecoveryAuditCertificate
from types import MappingProxyType
from tools.recovery_audit_certificate_v77_10 import digest,load,summary
def verify_output(o:Path):
 r=load(o/"recovery_audit_certificate_verification_v77_10.json")
 c=load(o/"recovery_audit_certificate_v77_10.json");s=load(o/"recovery_audit_certificate_summary_v77_10.json");e=[]
 if r.get("verification_sha256")!=digest({k:v for k,v in r.items() if k not in {"verification_sha256","issued_at_utc"}}):e.append("self-hash")
 if r.get("certificate")!=c:e.append("certificate mismatch")
 if summary(r)!=s:e.append("summary mismatch")
 cert=RecoveryAuditCertificate(c["schema_version"],c["certificate_id"],c["status"],c["chain_start_version"],
 c["chain_end_version"],c["stage_count"],tuple(MappingProxyType(x) for x in c["stages"]),
 MappingProxyType(c["safety_policy"]),MappingProxyType(c["state_continuity"]),c["certificate_sha256"])
 if not RecoveryAuditCertificateBuilder().verify(cert):e.append("certificate integrity")
 for ok,n in ((r.get("status")=="PASS","status"),(c.get("stage_count")==5,"stages"),
 (r.get("verification_result",{}).get("failed_gate_count")==0,"gates"),
 (all(c.get("safety_policy",{}).values()),"safety"),(all(c.get("state_continuity",{}).values()),"continuity"),
 (r.get("next_phase")=="V77_11_RECOVERY_RELEASE_MANIFEST","next")):
  if not ok:e.append(n)
 return {"verified":not e,"status":"PASS" if not e else "FAIL","error_count":len(e),"errors":e,
 "recovery_audit_certificate_sha256":c.get("certificate_sha256"),
 "verification_sha256":r.get("verification_sha256"),"stage_count":c.get("stage_count"),
 "next_phase":r.get("next_phase")}
def main():
 p=argparse.ArgumentParser();p.add_argument("--output-dir",required=True);r=verify_output(Path(p.parse_args().output_dir));print(json.dumps(r,indent=2));return 0 if r["verified"] else 1
if __name__=="__main__":raise SystemExit(main())
