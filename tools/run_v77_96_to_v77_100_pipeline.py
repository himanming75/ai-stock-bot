from pathlib import Path
import argparse,json,shutil,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from broker_integration.broker_integration_pipeline_v77_96_100 import *

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--repository-root",default=".")
    p.add_argument("--clean",action="store_true")
    a=p.parse_args()
    r=Path(a.repository_root).resolve()
    cert95=r/"release/v77_95/output/live_readiness_certificate_v77_95.json"
    cfg=r/"release/v77_96/config/broker_integration_config_v77_96.json"
    for f in (cert95,cfg):
        if not f.is_file():raise SystemExit(f"Missing required input: {f}")
    out={v:r/f"release/v{v}/output" for v in ("77_96","77_97","77_98","77_99","77_100")}
    if a.clean:
        for d in out.values():shutil.rmtree(d,ignore_errors=True)
    p96=build_broker_integration_skeleton(cert95,cfg,out["77_96"])
    p97=build_broker_interface_contract(out["77_96"]/"broker_integration_skeleton_v77_96.json",out["77_97"])
    p98=run_offline_broker_adapter_harness(out["77_97"]/"broker_interface_contract_v77_97.json",out["77_98"])
    p99=run_broker_integration_safety_gate(
        out["77_96"]/"broker_integration_skeleton_v77_96.json",
        out["77_97"]/"broker_interface_contract_v77_97.json",
        out["77_98"]/"offline_broker_adapter_harness_v77_98.json",
        out["77_99"])
    p100=issue_broker_integration_certificate(
        out["77_96"]/"broker_integration_skeleton_verification_v77_96.json",
        out["77_97"]/"broker_interface_contract_verification_v77_97.json",
        out["77_98"]/"offline_broker_adapter_harness_verification_v77_98.json",
        out["77_99"]/"broker_integration_safety_gate_verification_v77_99.json",
        out["77_96"]/"broker_integration_skeleton_v77_96.json",
        out["77_100"])
    stages=[p96,p97,p98,p99,p100]
    champion=p100.get("champion_candidate") or {}
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
        "next_phase":p100.get("next_phase")
    }
    summary["pipeline_sha256"]=digest_json({k:v for k,v in summary.items() if k!="pipeline_sha256"})
    write_json(out["77_100"]/"broker_integration_pipeline_summary_v77_96_to_v77_100.json",summary)
    print(json.dumps(summary,indent=2))
    return 0 if summary["status"]=="PASS" else 1

if __name__=="__main__":
    raise SystemExit(main())
