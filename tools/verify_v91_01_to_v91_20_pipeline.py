from pathlib import Path
import argparse,hashlib,json
def h(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");a=p.parse_args()
o=Path(a.repository_root).resolve()/"release/v91_20/output";c=json.loads((o/"actual_paper_optin_certificate_v91_20.json").read_text());v=json.loads((o/"actual_paper_optin_verify_v91_20.json").read_text());u=dict(c);e=u.pop("certificate_sha256");s=c["summary"]
checks={"certificate_hash_valid":e==h(u),"status_pass":c["status"]=="PASS","verify_flag_true":v["verified"] is True,
"required_approvals_two":s["required_approvals"]==2,"approval_count_two":s["approval_count"]==2,
"ttl_300":s["session_ttl_seconds"]==300,"single_use":s["max_session_uses"]==1,
"gate_ready":s["permission_gate_status"]=="READY_READ_ONLY","audit_pass":s["audit_status"]=="PASS",
"foundation_complete":c["actual_paper_automation_opt_in_foundation_complete"] is True,
"session_ready":c["read_only_automation_session_ready"] is True,
"kill_verified":c["kill_switch_verified"] is True,"revoke_verified":c["revocation_verified"] is True,
"scheduler_disabled":c["scheduler_enabled"] is False,"runtime_disabled":c["runtime_loop_enabled"] is False,
"paper_submit_disabled":c["paper_order_submission_authorized"] is False,
"write_zero":c["write_capability_count"]==0,"orders_zero":c["actual_orders_submitted"]==0}
f=[k for k,x in checks.items() if not x]
print(json.dumps({"stage_range":"V91.01-V91.20","status":"PASS" if not f else "FAIL","checks":checks,"failed_checks":f,"next_phase":c["next_phase"]},indent=2,sort_keys=True));raise SystemExit(0 if not f else 1)
