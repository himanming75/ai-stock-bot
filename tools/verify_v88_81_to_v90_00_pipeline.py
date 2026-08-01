from pathlib import Path
import argparse,json,hashlib
def h(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");a=p.parse_args()
o=Path(a.repository_root).resolve()/"release/v90_00/output"
c=json.loads((o/"fast_track_certificate_v90_00.json").read_text())
v=json.loads((o/"fast_track_verify_v90_00.json").read_text())
u=dict(c);e=u.pop("certificate_sha256")
checks={"certificate_hash_valid":e==h(u),"status_pass":c["status"]=="PASS",
"verify_flag_true":v["verified"] is True,"chain_four":c["summary"]["certificate_count"]==4,
"automation_certified":c["paper_automation_framework_certified"] is True,
"portfolio_complete":c["portfolio_runtime_foundation_complete"] is True,
"risk_complete":c["runtime_risk_engine_complete"] is True,
"rc1_ready":c["paper_runtime_rc1_ready"] is True,
"scheduler_disabled":c["scheduler_enabled"] is False,
"runtime_disabled":c["runtime_loop_enabled"] is False,
"network_disabled":c["market_data_network_enabled"] is False,
"paper_submit_disabled":c["paper_order_submission_authorized"] is False,
"network_zero":c["network_requests_executed"]==0,"orders_zero":c["actual_orders_submitted"]==0}
failed=[k for k,x in checks.items() if not x]
print(json.dumps({"stage_range":"V88.81-V90.00","status":"PASS" if not failed else "FAIL",
"checks":checks,"failed_checks":failed,"release_candidate":c["release_candidate"],
"next_phase":c["next_phase"]},indent=2,sort_keys=True))
raise SystemExit(0 if not failed else 1)
