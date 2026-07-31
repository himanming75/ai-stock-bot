from pathlib import Path
import argparse,json,shutil,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from market_data.market_data_pipeline_v78_31_35 import *
def main():
    p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");p.add_argument("--clean",action="store_true")
    a=p.parse_args();r=Path(a.repository_root).resolve()
    cert=r/"release/v78_30/output/market_clock_certificate_v78_30.json"
    cfg=r/"release/v78_31/config/market_data_config_v78_31.json"
    for f in (cert,cfg):
        if not f.is_file():raise SystemExit(f"Missing required input: {f}")
    out={v:r/f"release/v{v}/output" for v in ("78_31","78_32","78_33","78_34","78_35")}
    if a.clean:
        for d in out.values():shutil.rmtree(d,ignore_errors=True)
    p31=build_market_data_foundation(cert,cfg,out["78_31"])
    p32=run_offline_quote_bar_feed(out["78_31"]/"market_data_adapter_foundation_v78_31.json",out["78_32"])
    p33=run_market_data_validation(out["78_31"]/"market_data_adapter_foundation_v78_31.json",
        out["78_32"]/"offline_quote_bar_feed_v78_32.json",out["78_33"])
    p34=run_market_data_safety_gate(out["78_31"]/"market_data_adapter_foundation_v78_31.json",
        out["78_32"]/"offline_quote_bar_feed_v78_32.json",
        out["78_33"]/"market_data_validation_gap_detection_v78_33.json",out["78_34"])
    p35=issue_market_data_certificate(
        out["78_31"]/"market_data_adapter_foundation_verification_v78_31.json",
        out["78_32"]/"offline_quote_bar_feed_verification_v78_32.json",
        out["78_33"]/"market_data_validation_gap_detection_verification_v78_33.json",
        out["78_34"]/"market_data_safety_gate_verification_v78_34.json",
        out["78_31"]/"market_data_adapter_foundation_v78_31.json",out["78_35"])
    stages=[p31,p32,p33,p34,p35];champion=p35.get("champion_candidate") or {}
    summary={"status":"PASS" if all(x.get("status")=="PASS" for x in stages) else "FAIL","stage_count":5,
      "passed_stage_count":sum(x.get("status")=="PASS" for x in stages),
      "failed_stage_count":sum(x.get("status")!="PASS" for x in stages),**safety(),
      "champion_candidate_id":champion.get("candidate_id"),
      "failed_stages":[{"stage":x.get("stage"),"errors":x.get("errors",[]),"failed_checks":x.get("failed_checks",[])}
                       for x in stages if x.get("status")!="PASS"],
      "next_phase":p35.get("next_phase")}
    summary["pipeline_sha256"]=digest_json({k:v for k,v in summary.items() if k!="pipeline_sha256"})
    write_json(out["78_35"]/"market_data_pipeline_summary_v78_31_to_v78_35.json",summary)
    print(json.dumps(summary,indent=2));return 0 if summary["status"]=="PASS" else 1
if __name__=="__main__":raise SystemExit(main())
