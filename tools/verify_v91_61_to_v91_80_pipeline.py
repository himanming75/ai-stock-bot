from pathlib import Path
import argparse,hashlib,json
def h(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");a=p.parse_args()
o=Path(a.repository_root).resolve()/"release/v91_80/output";c=json.loads((o/"actual_paper_rc2_certification_v91_80.json").read_text());v=json.loads((o/"actual_paper_rc2_verify_v91_80.json").read_text());u=dict(c);e=u.pop("certificate_sha256");s=c["summary"]
checks={"certificate_hash_valid":e==h(u),"status_pass":c["status"]=="PASS","verify_flag_true":v["verified"] is True,
"source_stage_v91_60":s["source_stage"]=="V91.60","replay_pass":s["replay_status"]=="PASS",
"restart_pass":s["restart_status"]=="PASS","recovery_pass":s["recovery_status"]=="PASS",
"recovery_scenarios_five":s["recovery_scenario_count"]==5,"integrity_pass":s["integrity_status"]=="PASS",
"rollback_pass":s["rollback_status"]=="PASS","acceptance_pass":s["acceptance_status"]=="PASS","audit_pass":s["audit_status"]=="PASS",
"cert_complete":c["actual_paper_automation_rc2_certification_complete"] is True,
"rc2_ready":c["actual_paper_automation_rc2_certified_read_only_ready"] is True,
"replay_verified":c["deterministic_replay_verified"] is True,"restart_certified":c["restart_certified"] is True,
"recovery_certified":c["recovery_certified"] is True,"tamper_verified":c["tamper_detection_verified"] is True,
"rollback_certified":c["rollback_certified"] is True,"acceptance_verified":c["release_acceptance_verified"] is True,
"scheduler_disabled":c["scheduler_enabled"] is False,"runtime_disabled":c["runtime_loop_enabled"] is False,
"paper_submit_disabled":c["paper_order_submission_authorized"] is False,
"write_zero":c["write_capability_count"]==0,"network_zero":c["network_requests_executed"]==0,
"orders_zero":c["actual_orders_submitted"]==0}
f=[k for k,x in checks.items() if not x]
print(json.dumps({"stage_range":"V91.61-V91.80","status":"PASS" if not f else "FAIL","release_candidate":c["release_candidate"],"checks":checks,"failed_checks":f,"next_phase":c["next_phase"]},indent=2,sort_keys=True));raise SystemExit(0 if not f else 1)
