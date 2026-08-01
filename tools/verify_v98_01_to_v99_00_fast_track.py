from pathlib import Path
import argparse,hashlib,json
def h(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");a=p.parse_args()
o=Path(a.repository_root).resolve()/"release/v99_00/output"
c=json.loads((o/"multi_session_certificate_v99_00.json").read_text())
v=json.loads((o/"multi_session_verify_v99_00.json").read_text())
u=dict(c);e=u.pop("certificate_sha256");s=c["summary"]
checks={"certificate_hash_valid":e==h(u),"status_pass":c["status"]=="PASS",
"verify_flag_true":v["verified"] is True,"queue_three":s["initial_queue_depth"]==3,
"single_active":s["max_active_sessions"]==1,"first_closed":s["first_session_status"]=="CLOSED",
"second_closed":s["second_session_status"]=="CLOSED",
"concurrent_blocked":s["concurrent_status"]=="BLOCKED_CONCURRENT",
"token_rotated":s["token_rotation_status"]=="ROTATED",
"cleanup_positive":s["expired_cleanup_count"]>=1,
"recovery_scenarios_seven":s["recovery_scenario_count"]==7,
"audit_records_eight":s["audit_record_count"]==8,
"rollback_pass":s["rollback_status"]=="PASS","default_safety_pass":s["default_safety_status"]=="PASS",
"fast_track_complete":c["multi_session_validation_fast_track_complete"] is True,
"rc3_ready":c["actual_paper_multi_session_validation_rc3_ready"] is True,
"default_network_zero":c["default_network_requests_executed"]==0,
"default_orders_zero":c["default_actual_orders_submitted"]==0}
f=[k for k,x in checks.items() if not x]
print(json.dumps({"stage_range":"V98.01-V99.00","status":"PASS" if not f else "FAIL",
"release_candidate":c["release_candidate"],"checks":checks,"failed_checks":f,
"next_phase":c["next_phase"]},indent=2,sort_keys=True))
raise SystemExit(0 if not f else 1)
