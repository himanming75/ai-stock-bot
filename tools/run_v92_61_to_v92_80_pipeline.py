from pathlib import Path
import argparse,json,shutil,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from alpaca_market_data.actual_paper_e2e_submission_certification_v92_61_80 import *
p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");p.add_argument("--clean",action="store_true");a=p.parse_args()
root=Path(a.repository_root).resolve();out=root/"release/v92_80/output"
if a.clean and out.exists():shutil.rmtree(out)
c=E2ECertificationConfig();r=run_engine(root,c,out);cert=build_certificate(out,c,r)
print(json.dumps({"stage_range":"V92.61-V92.80","status":cert["status"],
"release_candidate":cert["release_candidate"],**cert["summary"],
"actual_paper_end_to_end_submission_certification_complete":cert["actual_paper_end_to_end_submission_certification_complete"],
"actual_paper_e2e_submission_preview_rc1_ready":cert["actual_paper_e2e_submission_preview_rc1_ready"],
"source_chain_verified":cert["source_chain_verified"],"e2e_flow_verified":cert["e2e_flow_verified"],
"idempotency_verified":cert["idempotency_verified"],"reconciliation_verified":cert["reconciliation_verified"],
"failure_containment_verified":cert["failure_containment_verified"],
"rollback_certified":cert["rollback_certified"],"tamper_detection_verified":cert["tamper_detection_verified"],
"release_acceptance_verified":cert["release_acceptance_verified"],
"paper_order_submission_authorized":False,"write_capability_count":0,
"network_requests_executed":0,"actual_orders_submitted":0,
"next_phase":cert["next_phase"]},indent=2,sort_keys=True))
raise SystemExit(0 if cert["status"]=="PASS" else 1)
