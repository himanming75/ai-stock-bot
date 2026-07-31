from __future__ import annotations
from pathlib import Path
import argparse,json,shutil,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from broker.recovery_release_pipeline_v77_11_15 import *

def main():
 p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");p.add_argument("--clean",action="store_true");a=p.parse_args()
 r=Path(a.repository_root).resolve()
 cert=r/"release/v77_10/output/recovery_audit_certificate_v77_10.json"
 out={v:r/f"release/v{v}/output" for v in ("77_11","77_12","77_13","77_14","77_15")}
 if a.clean:
  for pth in out.values():shutil.rmtree(pth,ignore_errors=True)
 s11=build_manifest(r,cert,out["77_11"],sha256_file(cert))
 m=out["77_11"]/"recovery_release_manifest_v77_11.json"
 s12=build_bundle(r,m,out["77_12"])
 b=out["77_12"]/"recovery_bundle_v77_12.zip"
 s13=verify_bundle(b,m,out["77_13"])
 s14=validate_installation(b,m,out["77_14"])
 s15=issue_release_certificate(
  out["77_11"]/"recovery_release_manifest_verification_v77_11.json",
  out["77_12"]/"recovery_bundle_builder_verification_v77_12.json",
  out["77_13"]/"recovery_bundle_integrity_verification_v77_13.json",
  out["77_14"]/"recovery_installation_validator_verification_v77_14.json",
  out["77_15"])
 stages=[s11,s12,s13,s14,s15]
 result={"status":"PASS" if all(x.status=="PASS" for x in stages) else "FAIL",
         "stage_count":5,"passed_stage_count":sum(x.status=="PASS" for x in stages),
         "failed_stage_count":sum(x.status!="PASS" for x in stages),
         "stages":[x.as_dict() for x in stages],
         "environment":"offline","network_allowed":False,"broker_connected":False,
         "actual_orders_submitted":0,"live_trading_authorized":False,
         "next_phase":s15.next_phase}
 result["pipeline_sha256"]=digest_json({k:v for k,v in result.items() if k!="pipeline_sha256"})
 write_json(r/"release/v77_15/output/recovery_release_pipeline_summary_v77_11_to_v77_15.json",result)
 print(json.dumps(result,indent=2))
 return 0 if result["status"]=="PASS" else 1
if __name__=="__main__":raise SystemExit(main())
