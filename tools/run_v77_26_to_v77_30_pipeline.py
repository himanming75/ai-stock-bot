from pathlib import Path
import argparse, json, shutil, sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from broker.market_data_pipeline_v77_26_30 import *
def main():
    p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");p.add_argument("--clean",action="store_true")
    p.add_argument("--symbol",default="SPY");p.add_argument("--bar-count",type=int,default=30);p.add_argument("--interval-seconds",type=int,default=60);a=p.parse_args()
    r=Path(a.repository_root).resolve()
    cert=r/"release/v77_25/output/scheduled_runtime_audit_certificate_v77_25.json"
    if not cert.is_file():raise SystemExit("Missing V77.25 output certificate. Run V77.21-V77.25 pipeline first.")
    out={v:r/f"release/v{v}/output" for v in ("77_26","77_27","77_28","77_29","77_30")}
    if a.clean:
        for pth in out.values():shutil.rmtree(pth,ignore_errors=True)
    s26=build_paper_market_data_feed(cert,out["77_26"],symbol=a.symbol,bar_count=a.bar_count,interval_seconds=a.interval_seconds)
    feed=out["77_26"]/"paper_market_data_feed_v77_26.json"
    s27=build_market_data_validation_ledger(feed,out["77_27"])
    ledger=out["77_27"]/"market_data_validation_ledger_v77_27.json"
    s28=detect_stale_data_gaps(feed,ledger,out["77_28"])
    detector=out["77_28"]/"stale_data_gap_detector_v77_28.json"
    s29=recover_market_data(feed,detector,out["77_29"])
    s30=issue_market_data_certificate(
        out["77_26"]/"paper_market_data_feed_verification_v77_26.json",
        out["77_27"]/"market_data_validation_ledger_verification_v77_27.json",
        out["77_28"]/"stale_data_gap_detector_verification_v77_28.json",
        out["77_29"]/"market_data_recovery_engine_verification_v77_29.json",
        out["77_30"])
    stages=[s26,s27,s28,s29,s30]
    summary={"status":"PASS" if all(x.status=="PASS" for x in stages) else "FAIL","stage_count":5,
        "passed_stage_count":sum(x.status=="PASS" for x in stages),"failed_stage_count":sum(x.status!="PASS" for x in stages),
        "stages":[x.as_dict() for x in stages],**safety(),"next_phase":s30.next_phase}
    summary["pipeline_sha256"]=digest_json({k:v for k,v in summary.items() if k!="pipeline_sha256"})
    write_json(out["77_30"]/"market_data_pipeline_summary_v77_26_to_v77_30.json",summary)
    print(json.dumps(summary,indent=2));return 0 if summary["status"]=="PASS" else 1
if __name__=="__main__":raise SystemExit(main())
