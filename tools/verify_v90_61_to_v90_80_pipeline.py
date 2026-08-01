from pathlib import Path
import argparse,hashlib,json
def h(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");a=p.parse_args()
o=Path(a.repository_root).resolve()/"release/v90_80/output"
c=json.loads((o/"actual_paper_release_candidate_certificate_v90_80.json").read_text())
v=json.loads((o/"actual_paper_release_candidate_verify_v90_80.json").read_text())
u=dict(c);e=u.pop("certificate_sha256");s=c["summary"]
checks={"certificate_hash_valid":e==h(u),"status_pass":c["status"]=="PASS","verify_flag_true":v["verified"] is True,
"checklist_complete":s["checklist_completed"]==s["checklist_required"],"health_gate_pass":s["health_gate_status"]=="PASS",
"startup_ready":s["startup_state"]=="READY_READ_ONLY","shutdown_stopped":s["shutdown_state"]=="STOPPED",
"acceptance_pass":s["acceptance_status"]=="PASS","audit_pass":s["audit_status"]=="PASS",
"rc_complete":c["actual_paper_release_candidate_complete"] is True,
"rc1_ready":c["actual_paper_read_only_operations_rc1_ready"] is True,
"incident_verified":c["incident_response_verified"] is True,"rollback_verified":c["rollback_verified"] is True,
"scheduler_disabled":c["scheduler_enabled"] is False,"runtime_disabled":c["runtime_loop_enabled"] is False,
"write_zero":c["write_capability_count"]==0,"network_zero":c["network_requests_executed"]==0,
"orders_zero":c["actual_orders_submitted"]==0}
f=[k for k,x in checks.items() if not x]
print(json.dumps({"stage_range":"V90.61-V90.80","status":"PASS" if not f else "FAIL",
"release_candidate":c["release_candidate"],"checks":checks,"failed_checks":f,"next_phase":c["next_phase"]},indent=2,sort_keys=True))
raise SystemExit(0 if not f else 1)
