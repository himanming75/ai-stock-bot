from pathlib import Path
import argparse,json,shutil,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from broker.strategy_input_pipeline_v77_31_35 import *
def main():
    p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");p.add_argument("--clean",action="store_true");a=p.parse_args()
    r=Path(a.repository_root).resolve()
    cert=r/"release/v77_30/output/market_data_audit_certificate_v77_30.json"
    feed=r/"release/v77_26/output/paper_market_data_feed_v77_26.json"
    if not cert.is_file() or not feed.is_file():raise SystemExit("Missing V77.30 certificate or V77.26 feed.")
    out={v:r/f"release/v{v}/output" for v in ("77_31","77_32","77_33","77_34","77_35")}
    if a.clean:
        for x in out.values():shutil.rmtree(x,ignore_errors=True)
    s31=build_strategy_input(cert,feed,out["77_31"])
    si=out["77_31"]/"ai_strategy_input_v77_31.json"
    s32=build_feature_validation_ledger(si,out["77_32"])
    ledger=out["77_32"]/"strategy_feature_validation_ledger_v77_32.json"
    s33=generate_strategy_signal(si,ledger,out["77_33"])
    signal=out["77_33"]/"strategy_signal_v77_33.json"
    s34=run_signal_safety_gate(signal,si,out["77_34"])
    s35=issue_strategy_input_certificate(
        out["77_31"]/"ai_strategy_input_verification_v77_31.json",
        out["77_32"]/"strategy_feature_validation_ledger_verification_v77_32.json",
        out["77_33"]/"strategy_signal_verification_v77_33.json",
        out["77_34"]/"signal_safety_gate_verification_v77_34.json",out["77_35"])
    stages=[s31,s32,s33,s34,s35]
    summary={"status":"PASS" if all(x.status=="PASS" for x in stages) else "FAIL","stage_count":5,
        "passed_stage_count":sum(x.status=="PASS" for x in stages),"failed_stage_count":sum(x.status!="PASS" for x in stages),
        "stages":[x.as_dict() for x in stages],**safety(),"next_phase":s35.next_phase}
    summary["pipeline_sha256"]=digest_json({k:v for k,v in summary.items() if k!="pipeline_sha256"})
    write_json(out["77_35"]/"strategy_input_pipeline_summary_v77_31_to_v77_35.json",summary)
    print(json.dumps(summary,indent=2));return 0 if summary["status"]=="PASS" else 1
if __name__=="__main__":raise SystemExit(main())
