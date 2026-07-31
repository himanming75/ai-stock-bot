from __future__ import annotations
from pathlib import Path
import argparse,json,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from broker.recovery_release_pipeline_v77_11_15 import load_json,digest_json
def main():
 p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");a=p.parse_args();r=Path(a.repository_root)
 s=load_json(r/"release/v77_15/output/recovery_release_pipeline_summary_v77_11_to_v77_15.json")
 errors=[]
 if s.get("status")!="PASS":errors.append("pipeline_status")
 if s.get("stage_count")!=5 or s.get("passed_stage_count")!=5:errors.append("stage_count")
 if s.get("failed_stage_count")!=0:errors.append("failed_stages")
 if s.get("actual_orders_submitted")!=0:errors.append("orders")
 expected=digest_json({k:v for k,v in s.items() if k!="pipeline_sha256"})
 if s.get("pipeline_sha256")!=expected:errors.append("pipeline_sha256")
 result={"verified":not errors,"status":"PASS" if not errors else "FAIL","error_count":len(errors),"errors":errors,
         "pipeline_sha256":s.get("pipeline_sha256"),"next_phase":s.get("next_phase")}
 print(json.dumps(result,indent=2));return 0 if not errors else 1
if __name__=="__main__":raise SystemExit(main())
