from pathlib import Path
import argparse,json,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from broker.risk_management_pipeline_v77_36_40 import load_json,digest_json
def main():
    p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");a=p.parse_args();r=Path(a.repository_root)
    s=load_json(r/"release/v77_40/output/risk_management_pipeline_summary_v77_36_to_v77_40.json");errors=[]
    if s.get("status")!="PASS" or s.get("stage_count")!=5 or s.get("passed_stage_count")!=5 or s.get("failed_stage_count")!=0:errors.append("pipeline")
    if s.get("environment")!="offline" or s.get("network_allowed") is not False:errors.append("offline_safety")
    if s.get("broker_connected") is not False or s.get("actual_orders_submitted")!=0 or s.get("live_trading_authorized") is not False:errors.append("trading_safety")
    if s.get("pipeline_sha256")!=digest_json({k:v for k,v in s.items() if k!="pipeline_sha256"}):errors.append("pipeline_sha256")
    result={"verified":not errors,"status":"PASS" if not errors else "FAIL","error_count":len(errors),"errors":errors,
      "pipeline_sha256":s.get("pipeline_sha256"),"next_phase":s.get("next_phase")}
    print(json.dumps(result,indent=2));return 0 if not errors else 1
if __name__=="__main__":raise SystemExit(main())
