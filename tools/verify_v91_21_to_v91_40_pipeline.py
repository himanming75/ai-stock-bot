from pathlib import Path
import argparse,hashlib,json
def h(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");a=p.parse_args()
o=Path(a.repository_root).resolve()/"release/v91_40/output";c=json.loads((o/"actual_paper_session_certificate_v91_40.json").read_text());v=json.loads((o/"actual_paper_session_verify_v91_40.json").read_text());u=dict(c);e=u.pop("certificate_sha256");s=c["summary"]
checks={"certificate_hash_valid":e==h(u),"status_pass":c["status"]=="PASS","verify_flag_true":v["verified"] is True,
"ttl_300":s["session_ttl_seconds"]==300,"heartbeat_interval_30":s["heartbeat_interval_seconds"]==30,
"heartbeat_count_two":s["heartbeat_count"]==2,"resume_read_only":s["resume_status"]=="RESUMED_READ_ONLY",
"consumed":s["consumed_status"]=="CONSUMED","revoked":s["revoked_status"]=="REVOKED","closed":s["closed_status"]=="CLOSED",
"audit_pass":s["audit_status"]=="PASS","validation_complete":c["actual_paper_automation_session_validation_complete"] is True,
"lifecycle_verified":c["read_only_session_lifecycle_verified"] is True,"heartbeat_verified":c["session_heartbeat_verified"] is True,
"kill_verified":c["kill_switch_verified"] is True,"shutdown_verified":c["normal_shutdown_verified"] is True,
"scheduler_disabled":c["scheduler_enabled"] is False,"runtime_disabled":c["runtime_loop_enabled"] is False,
"paper_submit_disabled":c["paper_order_submission_authorized"] is False,"write_zero":c["write_capability_count"]==0,
"orders_zero":c["actual_orders_submitted"]==0}
f=[k for k,x in checks.items() if not x]
print(json.dumps({"stage_range":"V91.21-V91.40","status":"PASS" if not f else "FAIL","checks":checks,"failed_checks":f,"next_phase":c["next_phase"]},indent=2,sort_keys=True));raise SystemExit(0 if not f else 1)
