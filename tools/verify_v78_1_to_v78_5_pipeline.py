from pathlib import Path
import argparse,json,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from paper_broker.paper_broker_pipeline_v78_1_5 import load_json,digest_json

def main():
    p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".")
    a=p.parse_args();r=Path(a.repository_root).resolve()
    path=r/"release/v78_5/output/paper_broker_pipeline_summary_v78_1_to_v78_5.json"
    errors=[];doc={}
    if not path.is_file():errors.append("summary_missing")
    else:doc=load_json(path)
    if doc:
        if doc.get("pipeline_sha256")!=digest_json({k:v for k,v in doc.items() if k!="pipeline_sha256"}):
            errors.append("pipeline_sha256")
        if doc.get("status")!="PASS":errors.append("pipeline_status")
        if doc.get("passed_stage_count")!=5:errors.append("stage_count")
        if doc.get("actual_orders_submitted")!=0:errors.append("actual_orders_submitted")
        if doc.get("network_allowed") is not False:errors.append("network_allowed")
        if doc.get("broker_connected") is not False:errors.append("broker_connected")
    result={"verified":not errors,"status":"PASS" if not errors else "FAIL",
            "error_count":len(errors),"errors":errors,
            "pipeline_sha256":doc.get("pipeline_sha256"),
            "champion_candidate_id":doc.get("champion_candidate_id"),
            "next_phase":doc.get("next_phase")}
    print(json.dumps(result,indent=2))
    return 0 if not errors else 1
if __name__=="__main__":raise SystemExit(main())
