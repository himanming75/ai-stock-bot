from pathlib import Path
import argparse,json,shutil,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from market_clock.market_clock_pipeline_v78_26_30 import *
def main():
    p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");p.add_argument("--clean",action="store_true")
    a=p.parse_args();r=Path(a.repository_root).resolve()
    cert=r/"release/v78_25/output/runtime_scheduler_certificate_v78_25.json"
    cfg=r/"release/v78_26/config/market_clock_config_v78_26.json"
    for f in (cert,cfg):
        if not f.is_file():raise SystemExit(f"Missing required input: {f}")
    out={v:r/f"release/v{v}/output" for v in ("78_26","78_27","78_28","78_29","78_30")}
    if a.clean:
        for d in out.values():shutil.rmtree(d,ignore_errors=True)
    p26=build_market_clock_foundation(cert,cfg,out["78_26"])
    p27=build_trading_session_calendar(out["78_26"]/"market_clock_foundation_v78_26.json",out["78_27"])
    p28=run_market_transition_engine(out["78_26"]/"market_clock_foundation_v78_26.json",out["78_28"])
    p29=run_market_clock_safety_gate(
        out["78_26"]/"market_clock_foundation_v78_26.json",
        out["78_27"]/"trading_session_calendar_v78_27.json",
        out["78_28"]/"market_open_close_transition_engine_v78_28.json",out["78_29"])
    p30=issue_market_clock_certificate(
        out["78_26"]/"market_clock_foundation_verification_v78_26.json",
        out["78_27"]/"trading_session_calendar_verification_v78_27.json",
        out["78_28"]/"market_open_close_transition_engine_verification_v78_28.json",
        out["78_29"]/"market_clock_safety_gate_verification_v78_29.json",
        out["78_26"]/"market_clock_foundation_v78_26.json",out["78_30"])
    stages=[p26,p27,p28,p29,p30];champion=p30.get("champion_candidate") or {}
    summary={"status":"PASS" if all(x.get("status")=="PASS" for x in stages) else "FAIL",
      "stage_count":5,"passed_stage_count":sum(x.get("status")=="PASS" for x in stages),
      "failed_stage_count":sum(x.get("status")!="PASS" for x in stages),**safety(),
      "champion_candidate_id":champion.get("candidate_id"),
      "failed_stages":[{"stage":x.get("stage"),"errors":x.get("errors",[]),"failed_checks":x.get("failed_checks",[])}
                       for x in stages if x.get("status")!="PASS"],
      "next_phase":p30.get("next_phase")}
    summary["pipeline_sha256"]=digest_json({k:v for k,v in summary.items() if k!="pipeline_sha256"})
    write_json(out["78_30"]/"market_clock_pipeline_summary_v78_26_to_v78_30.json",summary)
    print(json.dumps(summary,indent=2));return 0 if summary["status"]=="PASS" else 1
if __name__=="__main__":raise SystemExit(main())
