from pathlib import Path
import argparse,json,shutil,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from alpaca_market_data.submission_enablement_fast_track_v93_01_v94_00 import *
p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");p.add_argument("--clean",action="store_true");a=p.parse_args()
root=Path(a.repository_root).resolve();out=root/"release/v94_00/output"
if a.clean and out.exists():shutil.rmtree(out)
c=FastTrackConfig();r=run_engine(root,c,out);cert=build_certificate(out,c,r)
print(json.dumps({"stage_range":"V93.01-V94.00","status":cert["status"],
"release_candidate":cert["release_candidate"],**cert["summary"],
"submission_enablement_fast_track_complete":cert["submission_enablement_fast_track_complete"],
"single_order_preview_rc1_ready":cert["single_order_preview_rc1_ready"],
"enablement_foundation_verified":cert["enablement_foundation_verified"],
"approval_session_verified":cert["approval_session_verified"],
"risk_gate_verified":cert["risk_gate_verified"],"offline_adapter_verified":cert["offline_adapter_verified"],
"mock_execution_verified":cert["mock_execution_verified"],"reconciliation_verified":cert["reconciliation_verified"],
"recovery_verified":cert["recovery_verified"],"rollback_verified":cert["rollback_verified"],
"tamper_detection_verified":cert["tamper_detection_verified"],
"paper_order_submission_authorized":False,"write_capability_count":0,
"network_requests_executed":0,"actual_orders_submitted":0,
"next_phase":cert["next_phase"]},indent=2,sort_keys=True))
raise SystemExit(0 if cert["status"]=="PASS" else 1)
