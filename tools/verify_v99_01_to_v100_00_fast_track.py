from pathlib import Path
import argparse,hashlib,json
def h(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");a=p.parse_args()
o=Path(a.repository_root).resolve()/"release/v100_00/output"
c=json.loads((o/"v100_completion_certificate.json").read_text())
v=json.loads((o/"v100_completion_verify.json").read_text())
u=dict(c);e=u.pop("certificate_sha256");s=c["summary"]
checks={"certificate_hash_valid":e==h(u),"status_pass":c["status"]=="PASS",
"verify_flag_true":v["verified"] is True,"certificate_count_ten":s["certificate_count"]==10,
"readiness_pass":s["readiness_status"]=="PASS",
"checklist_complete":s["checklist_completed"]==s["checklist_required"],
"incident_scenarios_ten":s["incident_scenario_count"]==10,
"rollback_actions_ten":s["rollback_action_count"]==10,
"safety_lock_pass":s["safety_lock_status"]=="PASS",
"acceptance_pass":s["acceptance_status"]=="PASS",
"tamper_pass":s["tamper_status"]=="PASS","audit_pass":s["audit_status"]=="PASS",
"v100_complete":c["v100_final_production_candidate_complete"] is True,
"paper_candidate_ready":c["ai_stock_bot_paper_production_candidate_ready"] is True,
"paper_certified":c["paper_trading_system_certified"] is True,
"live_not_certified":c["live_trading_certified"] is False,
"default_network_zero":c["default_network_requests_executed"]==0,
"default_orders_zero":c["default_actual_orders_submitted"]==0}
f=[k for k,x in checks.items() if not x]
print(json.dumps({"stage_range":"V99.01-V100.00","status":"PASS" if not f else "FAIL",
"release_candidate":c["release_candidate"],"checks":checks,"failed_checks":f,
"next_phase":c["next_phase"]},indent=2,sort_keys=True))
raise SystemExit(0 if not f else 1)
