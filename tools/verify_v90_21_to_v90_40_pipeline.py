from pathlib import Path
import argparse,json,hashlib
def h(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");a=p.parse_args()
o=Path(a.repository_root).resolve()/"release/v90_40/output";c=json.loads((o/"read_only_runtime_certificate_v90_40.json").read_text());v=json.loads((o/"read_only_runtime_verify_v90_40.json").read_text());u=dict(c);e=u.pop("certificate_sha256");s=c["summary"]
checks={"certificate_hash_valid":e==h(u),"status_pass":c["status"]=="PASS","verify_flag_true":v["verified"] is True,
"poll_count_three":s["poll_count"]==3,"heartbeat_pass":s["heartbeat_status"]=="PASS","cache_pass":s["cache_status"]=="PASS",
"gate_ready":s["scheduler_gate_status"]=="READY_READ_ONLY","audit_pass":s["audit_status"]=="PASS",
"validation_complete":c["actual_paper_read_only_runtime_validation_complete"] is True,
"scheduler_disabled":c["scheduler_enabled"] is False,"runtime_disabled":c["runtime_loop_enabled"] is False,
"write_zero":c["write_capability_count"]==0,"orders_zero":c["actual_orders_submitted"]==0}
f=[k for k,x in checks.items() if not x]
print(json.dumps({"stage_range":"V90.21-V90.40","status":"PASS" if not f else "FAIL","checks":checks,"failed_checks":f,"next_phase":c["next_phase"]},indent=2,sort_keys=True));raise SystemExit(0 if not f else 1)
