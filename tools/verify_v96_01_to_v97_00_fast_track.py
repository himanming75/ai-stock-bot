from pathlib import Path
import argparse,hashlib,json
def h(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");a=p.parse_args()
o=Path(a.repository_root).resolve()/"release/v97_00/output"
c=json.loads((o/"controlled_validation_certificate_v97_00.json").read_text())
v=json.loads((o/"controlled_validation_verify_v97_00.json").read_text())
u=dict(c);e=u.pop("certificate_sha256");s=c["summary"]
checks={"certificate_hash_valid":e==h(u),"status_pass":c["status"]=="PASS",
"verify_flag_true":v["verified"] is True,"account_pass":s["account_status"]=="PASS",
"clock_pass":s["clock_status"]=="PASS","order_pass":s["order_status"]=="PASS",
"duplicate_blocked":s["duplicate_status"]=="BLOCKED_DUPLICATE",
"unknown_scenarios_five":s["unknown_scenario_count"]==5,
"cancel_policy_pass":s["cancel_policy_status"]=="PASS","rollback_pass":s["rollback_status"]=="PASS",
"fast_track_complete":c["controlled_execution_validation_fast_track_complete"] is True,
"validation_ready":c["actual_paper_controlled_execution_validation_rc1_ready"] is True,
"default_network_zero":c["default_network_requests_executed"]==0,
"default_orders_zero":c["default_actual_orders_submitted"]==0}
f=[k for k,x in checks.items() if not x]
print(json.dumps({"stage_range":"V96.01-V97.00","status":"PASS" if not f else "FAIL",
"release_candidate":c["release_candidate"],"checks":checks,"failed_checks":f,
"next_phase":c["next_phase"]},indent=2,sort_keys=True))
raise SystemExit(0 if not f else 1)
