from pathlib import Path
import argparse,json,shutil,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from risk_stress.risk_stress_pipeline_v77_86_90 import *

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--repository-root",default=".")
    p.add_argument("--clean",action="store_true")
    a=p.parse_args()
    r=Path(a.repository_root).resolve()
    cert85=r/"release/v77_85/output/monte_carlo_robustness_certificate_v77_85.json"
    cfg=r/"release/v77_86/config/risk_stress_config_v77_86.json"
    for f in (cert85,cfg):
        if not f.is_file():raise SystemExit(f"Missing required input: {f}")
    out={v:r/f"release/v{v}/output" for v in ("77_86","77_87","77_88","77_89","77_90")}
    if a.clean:
        for d in out.values():shutil.rmtree(d,ignore_errors=True)
    p86=build_risk_stress_engine(cert85,cfg,out["77_86"])
    p87=run_market_regime_shock_simulator(out["77_86"]/"risk_stress_engine_v77_86.json",out["77_87"])
    p88=analyze_liquidity_gap_risk(out["77_87"]/"market_regime_shock_results_v77_87.json",out["77_88"])
    p89=run_risk_stress_safety_gate(out["77_88"]/"liquidity_gap_risk_analysis_v77_88.json",cfg,out["77_89"])
    p90=issue_risk_stress_certificate(
        out["77_86"]/"risk_stress_engine_verification_v77_86.json",
        out["77_87"]/"market_regime_shock_verification_v77_87.json",
        out["77_88"]/"liquidity_gap_risk_analysis_verification_v77_88.json",
        out["77_89"]/"risk_stress_safety_gate_verification_v77_89.json",
        out["77_86"]/"risk_stress_engine_v77_86.json",
        out["77_88"]/"liquidity_gap_risk_analysis_v77_88.json",
        out["77_90"])
    stages=[p86,p87,p88,p89,p90]
    champion=p90.get("champion_candidate") or {}
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
        "next_phase":p90.get("next_phase")
    }
    summary["pipeline_sha256"]=digest_json({k:v for k,v in summary.items() if k!="pipeline_sha256"})
    write_json(out["77_90"]/"risk_stress_pipeline_summary_v77_86_to_v77_90.json",summary)
    print(json.dumps(summary,indent=2))
    return 0 if summary["status"]=="PASS" else 1

if __name__=="__main__":
    raise SystemExit(main())
