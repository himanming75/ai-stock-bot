from pathlib import Path
import argparse,hashlib,json
def h(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");a=p.parse_args()
o=Path(a.repository_root).resolve()/"release/v91_60/output";c=json.loads((o/"actual_paper_rc2_certificate_v91_60.json").read_text());v=json.loads((o/"actual_paper_rc2_verify_v91_60.json").read_text());u=dict(c);e=u.pop("certificate_sha256");s=c["summary"]
checks={"certificate_hash_valid":e==h(u),"status_pass":c["status"]=="PASS","verify_flag_true":v["verified"] is True,
"certificate_count_two":s["certificate_count"]==2,"persistence_pass":s["persistence_status"]=="PASS",
"recovery_pass":s["recovery_status"]=="PASS","recovery_scenarios_five":s["recovery_scenario_count"]==5,
"gate_ready":s["permission_gate_status"]=="READY_READ_ONLY","kill_pass":s["kill_switch_status"]=="PASS",
"acceptance_pass":s["acceptance_status"]=="PASS","audit_pass":s["audit_status"]=="PASS",
"foundation_complete":c["actual_paper_automation_rc2_foundation_complete"] is True,
"rc2_ready":c["actual_paper_automation_rc2_read_only_ready"] is True,
"persistence_verified":c["session_persistence_verified"] is True,
"recovery_verified":c["recovery_chain_verified"] is True,"permission_verified":c["permission_gate_verified"] is True,
"kill_verified":c["kill_switch_verified"] is True,"rollback_verified":c["rollback_verified"] is True,
"scheduler_disabled":c["scheduler_enabled"] is False,"runtime_disabled":c["runtime_loop_enabled"] is False,
"paper_submit_disabled":c["paper_order_submission_authorized"] is False,
"write_zero":c["write_capability_count"]==0,"orders_zero":c["actual_orders_submitted"]==0}
f=[k for k,x in checks.items() if not x]
print(json.dumps({"stage_range":"V91.41-V91.60","status":"PASS" if not f else "FAIL","release_candidate":c["release_candidate"],"checks":checks,"failed_checks":f,"next_phase":c["next_phase"]},indent=2,sort_keys=True));raise SystemExit(0 if not f else 1)
