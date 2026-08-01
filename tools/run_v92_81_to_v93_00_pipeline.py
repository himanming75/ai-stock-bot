from pathlib import Path
import argparse,json,shutil,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from alpaca_market_data.actual_paper_submission_release_candidate_v92_81_v93_00 import *
p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");p.add_argument("--clean",action="store_true");a=p.parse_args()
root=Path(a.repository_root).resolve();out=root/"release/v93_00/output"
if a.clean and out.exists():shutil.rmtree(out)
c=SubmissionReleaseCandidateConfig();r=run_engine(root,c,out);cert=build_certificate(out,c,r)
print(json.dumps({"stage_range":"V92.81-V93.00","status":cert["status"],
"release_candidate":cert["release_candidate"],**cert["summary"],
"actual_paper_submission_release_candidate_complete":cert["actual_paper_submission_release_candidate_complete"],
"actual_paper_submission_preview_rc1_ready":cert["actual_paper_submission_preview_rc1_ready"],
"rc_manifest_verified":cert["rc_manifest_verified"],"readiness_verified":cert["readiness_verified"],
"final_lock_verified":cert["final_lock_verified"],"release_acceptance_verified":cert["release_acceptance_verified"],
"rollback_verified":cert["rollback_verified"],"archive_verified":cert["archive_verified"],
"tamper_detection_verified":cert["tamper_detection_verified"],
"paper_order_submission_authorized":False,"write_capability_count":0,
"network_requests_executed":0,"actual_orders_submitted":0,
"next_phase":cert["next_phase"]},indent=2,sort_keys=True))
raise SystemExit(0 if cert["status"]=="PASS" else 1)
