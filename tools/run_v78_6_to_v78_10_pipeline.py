from pathlib import Path
import argparse,json,shutil,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from paper_event.paper_event_pipeline_v78_6_10 import *

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--repository-root",default=".")
    p.add_argument("--clean",action="store_true")
    a=p.parse_args()
    r=Path(a.repository_root).resolve()
    cert5=r/"release/v78_5/output/paper_broker_adapter_certificate_v78_5.json"
    cfg=r/"release/v78_6/config/paper_event_config_v78_6.json"
    for f in (cert5,cfg):
        if not f.is_file():raise SystemExit(f"Missing required input: {f}")
    out={v:r/f"release/v{v}/output" for v in ("78_6","78_7","78_8","78_9","78_10")}
    if a.clean:
        for d in out.values():shutil.rmtree(d,ignore_errors=True)
    p6=build_paper_event_engine(cert5,cfg,out["78_6"])
    p7=build_order_fill_event_ledger(out["78_6"]/"paper_event_engine_v78_6.json",out["78_7"])
    p8=run_event_replay_recovery(
        out["78_6"]/"paper_event_engine_v78_6.json",
        out["78_7"]/"order_fill_event_ledger_v78_7.json",
        out["78_8"])
    p9=run_paper_event_safety_gate(
        out["78_6"]/"paper_event_engine_v78_6.json",
        out["78_7"]/"order_fill_event_ledger_v78_7.json",
        out["78_8"]/"event_replay_recovery_v78_8.json",
        out["78_9"])
    p10=issue_paper_event_certificate(
        out["78_6"]/"paper_event_engine_verification_v78_6.json",
        out["78_7"]/"order_fill_event_ledger_verification_v78_7.json",
        out["78_8"]/"event_replay_recovery_verification_v78_8.json",
        out["78_9"]/"paper_event_safety_gate_verification_v78_9.json",
        out["78_6"]/"paper_event_engine_v78_6.json",
        out["78_10"])
    stages=[p6,p7,p8,p9,p10]
    champion=p10.get("champion_candidate") or {}
    summary={
        "status":"PASS" if all(x.get("status")=="PASS" for x in stages) else "FAIL",
        "stage_count":5,
        "passed_stage_count":sum(x.get("status")=="PASS" for x in stages),
        "failed_stage_count":sum(x.get("status")!="PASS" for x in stages),
        **safety(),
        "champion_candidate_id":champion.get("candidate_id"),
        "failed_stages":[{"stage":x.get("stage"),"errors":x.get("errors",[]),
                          "failed_checks":x.get("failed_checks",[])}
                         for x in stages if x.get("status")!="PASS"],
        "next_phase":p10.get("next_phase")
    }
    summary["pipeline_sha256"]=digest_json({k:v for k,v in summary.items() if k!="pipeline_sha256"})
    write_json(out["78_10"]/"paper_event_pipeline_summary_v78_6_to_v78_10.json",summary)
    print(json.dumps(summary,indent=2))
    return 0 if summary["status"]=="PASS" else 1

if __name__=="__main__":
    raise SystemExit(main())
