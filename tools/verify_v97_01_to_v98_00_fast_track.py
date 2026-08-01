from pathlib import Path
import argparse,hashlib,json
def h(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");a=p.parse_args()
o=Path(a.repository_root).resolve()/"release/v98_00/output"
c=json.loads((o/"controlled_session_certificate_v98_00.json").read_text())
v=json.loads((o/"controlled_session_verify_v98_00.json").read_text())
u=dict(c);e=u.pop("certificate_sha256");s=c["summary"]
checks={"certificate_hash_valid":e==h(u),"status_pass":c["status"]=="PASS","verify_flag_true":v["verified"] is True,
"session_closed":s["session_status"]=="CLOSED","heartbeats_two":s["heartbeat_count"]==2,
"heartbeat_30":s["heartbeat_interval_seconds"]==30,"ttl_300":s["session_ttl_seconds"]==300,
"duplicate_blocked":s["duplicate_status"]=="BLOCKED_DUPLICATE",
"resume_read_only":s["resume_status"]=="RESUMED_READ_ONLY","consumed":s["consume_status"]=="CONSUMED",
"recovery_scenarios_six":s["recovery_scenario_count"]==6,"rollback_pass":s["rollback_status"]=="PASS",
"default_safety_pass":s["default_safety_status"]=="PASS",
"fast_track_complete":c["controlled_session_execution_fast_track_complete"] is True,
"rc2_ready":c["actual_paper_controlled_session_rc2_ready"] is True,
"default_network_zero":c["default_network_requests_executed"]==0,
"default_orders_zero":c["default_actual_orders_submitted"]==0}
f=[k for k,x in checks.items() if not x]
print(json.dumps({"stage_range":"V97.01-V98.00","status":"PASS" if not f else "FAIL",
"release_candidate":c["release_candidate"],"checks":checks,"failed_checks":f,
"next_phase":c["next_phase"]},indent=2,sort_keys=True))
raise SystemExit(0 if not f else 1)
