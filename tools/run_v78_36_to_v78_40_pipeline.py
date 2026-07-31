from pathlib import Path
import argparse,json,shutil,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from strategy_runtime.strategy_runtime_pipeline_v78_36_40 import *

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--repository-root",default=".")
    p.add_argument("--clean",action="store_true")
    a=p.parse_args()
    r=Path(a.repository_root).resolve()
    cert=r/"release/v78_35/output/market_data_adapter_certificate_v78_35.json"
    cfg=r/"release/v78_36/config/strategy_runtime_config_v78_36.json"
    for f in (cert,cfg):
        if not f.is_file():
            raise SystemExit(f"Missing required input: {f}")

    out={v:r/f"release/v{v}/output" for v in ("78_36","78_37","78_38","78_39","78_40")}
    if a.clean:
        for d in out.values():
            shutil.rmtree(d,ignore_errors=True)

    p36=build_strategy_runtime_foundation(cert,cfg,out["78_36"])
    p37=build_strategy_registry_context(
        out["78_36"]/"strategy_runtime_foundation_v78_36.json",
        out["78_37"])
    p38=run_deterministic_signal_execution(
        out["78_36"]/"strategy_runtime_foundation_v78_36.json",
        out["78_38"])
    p39=run_strategy_runtime_safety_gate(
        out["78_36"]/"strategy_runtime_foundation_v78_36.json",
        out["78_37"]/"strategy_registry_runtime_context_v78_37.json",
        out["78_38"]/"deterministic_signal_execution_engine_v78_38.json",
        out["78_39"])
    p40=issue_strategy_runtime_certificate(
        out["78_36"]/"strategy_runtime_foundation_verification_v78_36.json",
        out["78_37"]/"strategy_registry_runtime_context_verification_v78_37.json",
        out["78_38"]/"deterministic_signal_execution_engine_verification_v78_38.json",
        out["78_39"]/"strategy_runtime_safety_gate_verification_v78_39.json",
        out["78_36"]/"strategy_runtime_foundation_v78_36.json",
        out["78_40"])

    stages=[p36,p37,p38,p39,p40]
    champion=p40.get("champion_candidate") or {}
    summary={
        "status":"PASS" if all(x.get("status")=="PASS" for x in stages) else "FAIL",
        "stage_count":5,
        "passed_stage_count":sum(x.get("status")=="PASS" for x in stages),
        "failed_stage_count":sum(x.get("status")!="PASS" for x in stages),
        **safety(),
        "champion_candidate_id":champion.get("candidate_id"),
        "failed_stages":[
            {"stage":x.get("stage"),"errors":x.get("errors",[]),"failed_checks":x.get("failed_checks",[])}
            for x in stages if x.get("status")!="PASS"
        ],
        "next_phase":p40.get("next_phase")
    }
    summary["pipeline_sha256"]=digest_json({k:v for k,v in summary.items() if k!="pipeline_sha256"})
    write_json(out["78_40"]/"strategy_runtime_pipeline_summary_v78_36_to_v78_40.json",summary)
    print(json.dumps(summary,indent=2))
    return 0 if summary["status"]=="PASS" else 1

if __name__=="__main__":
    raise SystemExit(main())
