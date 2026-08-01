from pathlib import Path
import argparse,json,shutil,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from alpaca_market_data.actual_paper_order_submission_gate_v92_21_40 import *
p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");p.add_argument("--clean",action="store_true");a=p.parse_args();root=Path(a.repository_root).resolve();out=root/"release/v92_40/output"
if a.clean and out.exists():shutil.rmtree(out)
c=SubmissionGateConfig();r=run_engine(root,c,out);x=build_certificate(out,c,r)
print(json.dumps({"stage_range":"V92.21-V92.40","status":x["status"],**x["summary"],"actual_paper_order_submission_gate_certification_complete":x["actual_paper_order_submission_gate_certification_complete"],"submission_gate_certified_preview_only":x["submission_gate_certified_preview_only"],"approval_gate_verified":x["approval_gate_verified"],"token_gate_verified":x["token_gate_verified"],"risk_gate_verified":x["risk_gate_verified"],"duplicate_gate_verified":x["duplicate_gate_verified"],"safety_gate_verified":x["safety_gate_verified"],"kill_switch_gate_verified":x["kill_switch_gate_verified"],"preview_gate_verified":x["preview_gate_verified"],"tamper_detection_verified":x["tamper_detection_verified"],"rollback_verified":x["rollback_verified"],"paper_order_submission_authorized":False,"write_capability_count":0,"network_requests_executed":0,"actual_orders_submitted":0,"next_phase":x["next_phase"]},indent=2,sort_keys=True));raise SystemExit(0 if x["status"]=="PASS" else 1)
