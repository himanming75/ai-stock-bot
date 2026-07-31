from pathlib import Path
import argparse,json,shutil,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from broker.risk_management_pipeline_v77_36_40 import *
def main():
    p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");p.add_argument("--clean",action="store_true")
    p.add_argument("--account-equity",type=float,default=100000.0);p.add_argument("--risk-per-trade-pct",type=float,default=0.01);a=p.parse_args()
    r=Path(a.repository_root).resolve()
    cert=r/"release/v77_35/output/strategy_input_audit_certificate_v77_35.json"
    strategy=r/"release/v77_31/output/ai_strategy_input_v77_31.json"
    signal_gate=r/"release/v77_34/output/signal_safety_gate_v77_34.json"
    if not all(x.is_file() for x in (cert,strategy,signal_gate)):raise SystemExit("Missing V77.35/V77.31/V77.34 outputs.")
    out={v:r/f"release/v{v}/output" for v in ("77_36","77_37","77_38","77_39","77_40")}
    if a.clean:
        for x in out.values():shutil.rmtree(x,ignore_errors=True)
    s36=calculate_position_risk(cert,strategy,signal_gate,out["77_36"],account_equity=a.account_equity,risk_per_trade_pct=a.risk_per_trade_pct)
    risk=out["77_36"]/"position_risk_calculator_v77_36.json"
    s37=apply_exposure_limits(risk,out["77_37"])
    exposure=out["77_37"]/"exposure_limit_engine_v77_37.json"
    s38=build_exit_policy(risk,exposure,out["77_38"])
    policy=out["77_38"]/"stop_loss_take_profit_policy_v77_38.json"
    s39=run_risk_decision_safety_gate(risk,exposure,policy,out["77_39"])
    s40=issue_risk_management_certificate(
        out["77_36"]/"position_risk_calculator_verification_v77_36.json",
        out["77_37"]/"exposure_limit_engine_verification_v77_37.json",
        out["77_38"]/"stop_loss_take_profit_policy_verification_v77_38.json",
        out["77_39"]/"risk_decision_safety_gate_verification_v77_39.json",out["77_40"])
    stages=[s36,s37,s38,s39,s40]
    summary={"status":"PASS" if all(x.status=="PASS" for x in stages) else "FAIL","stage_count":5,
        "passed_stage_count":sum(x.status=="PASS" for x in stages),"failed_stage_count":sum(x.status!="PASS" for x in stages),
        "stages":[x.as_dict() for x in stages],**safety(),"next_phase":s40.next_phase}
    summary["pipeline_sha256"]=digest_json({k:v for k,v in summary.items() if k!="pipeline_sha256"})
    write_json(out["77_40"]/"risk_management_pipeline_summary_v77_36_to_v77_40.json",summary)
    print(json.dumps(summary,indent=2));return 0 if summary["status"]=="PASS" else 1
if __name__=="__main__":raise SystemExit(main())
