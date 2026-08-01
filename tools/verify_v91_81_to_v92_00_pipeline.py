from pathlib import Path
import argparse,hashlib,json
def h(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");a=p.parse_args()
o=Path(a.repository_root).resolve()/"release/v92_00/output";c=json.loads((o/"actual_paper_order_optin_certificate_v92_00.json").read_text());v=json.loads((o/"actual_paper_order_optin_verify_v92_00.json").read_text());u=dict(c);e=u.pop("certificate_sha256");s=c["summary"]
checks={"certificate_hash_valid":e==h(u),"status_pass":c["status"]=="PASS","verify_flag_true":v["verified"] is True,
"approvals_two":s["required_approvals"]==2,"ttl_300":s["token_ttl_seconds"]==300,"single_use":s["max_token_uses"]==1,
"notional_500":s["max_order_notional"]==500.0,"quantity_5":s["max_quantity"]==5,"positions_3":s["max_open_positions"]==3,
"symbols_three":s["allowed_symbol_count"]==3,"gate_preview_only":s["submission_gate_status"]=="READY_PREVIEW_ONLY",
"audit_pass":s["audit_status"]=="PASS","foundation_complete":c["actual_paper_order_submission_opt_in_foundation_complete"] is True,
"token_ready":c["paper_order_preview_token_ready"] is True,"risk_verified":c["risk_limits_verified"] is True,
"duplicate_verified":c["duplicate_prevention_verified"] is True,"kill_verified":c["kill_switch_verified"] is True,
"paper_submit_disabled":c["paper_order_submission_authorized"] is False,"write_zero":c["write_capability_count"]==0,
"network_zero":c["network_requests_executed"]==0,"orders_zero":c["actual_orders_submitted"]==0}
f=[k for k,x in checks.items() if not x]
print(json.dumps({"stage_range":"V91.81-V92.00","status":"PASS" if not f else "FAIL","checks":checks,"failed_checks":f,"next_phase":c["next_phase"]},indent=2,sort_keys=True));raise SystemExit(0 if not f else 1)
