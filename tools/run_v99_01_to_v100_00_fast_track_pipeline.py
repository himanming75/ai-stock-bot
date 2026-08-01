from pathlib import Path
import argparse,json,shutil,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from alpaca_market_data.final_production_candidate_fast_track_v99_01_v100_00 import *
p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");p.add_argument("--clean",action="store_true");a=p.parse_args()
root=Path(a.repository_root).resolve();out=root/"release/v100_00/output"
if a.clean and out.exists():shutil.rmtree(out)
c=FinalCandidateConfig();r=run_engine(root,c,out);cert=build_certificate(out,c,r)
print(json.dumps({"stage_range":"V99.01-V100.00","status":cert["status"],
"release_candidate":cert["release_candidate"],**cert["summary"],
"v100_final_production_candidate_complete":cert["v100_final_production_candidate_complete"],
"ai_stock_bot_paper_production_candidate_ready":cert["ai_stock_bot_paper_production_candidate_ready"],
"certification_chain_verified":cert["certification_chain_verified"],
"release_readiness_verified":cert["release_readiness_verified"],
"operations_checklist_verified":cert["operations_checklist_verified"],
"incident_containment_verified":cert["incident_containment_verified"],
"rollback_package_verified":cert["rollback_package_verified"],
"final_safety_lock_verified":cert["final_safety_lock_verified"],
"final_acceptance_verified":cert["final_acceptance_verified"],
"tamper_detection_verified":cert["tamper_detection_verified"],
"final_audit_verified":cert["final_audit_verified"],
"paper_trading_system_certified":cert["paper_trading_system_certified"],
"live_trading_certified":cert["live_trading_certified"],
"default_network_requests_executed":0,"default_actual_orders_submitted":0,
"next_phase":cert["next_phase"]},indent=2,sort_keys=True))
raise SystemExit(0 if cert["status"]=="PASS" else 1)
