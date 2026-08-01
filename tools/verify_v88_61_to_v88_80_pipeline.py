from pathlib import Path
import argparse,json,hashlib
def h(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");a=p.parse_args()
o=Path(a.repository_root).resolve()/"release/v88_80/output"
c=json.loads((o/"scheduler_runtime_sim_certificate_v88_80.json").read_text())
v=json.loads((o/"scheduler_runtime_sim_verify_v88_80.json").read_text())
u=dict(c);e=u.pop("certificate_sha256")
checks={"certificate_hash_valid":e==h(u),"status_pass":c["status"]=="PASS",
"verify_flag_true":v["verified"] is True,"cycles_three":c["summary"]["cycle_count"]==3,
"signals_three":c["summary"]["signal_count"]==3,"final_state_stopped":c["summary"]["final_state"]=="STOPPED",
"audit_pass":c["summary"]["audit_status"]=="PASS",
"simulation_complete":c["scheduler_runtime_simulation_complete"] is True,
"daily_certified":c["daily_runtime_simulation_certified"] is True,
"scheduler_disabled":c["scheduler_enabled"] is False,"runtime_disabled":c["runtime_loop_enabled"] is False,
"network_zero":c["network_requests_executed"]==0,"orders_zero":c["actual_orders_submitted"]==0}
failed=[k for k,x in checks.items() if not x]
print(json.dumps({"stage_range":"V88.61-V88.80","status":"PASS" if not failed else "FAIL",
"checks":checks,"failed_checks":failed,"next_phase":c["next_phase"]},indent=2,sort_keys=True))
raise SystemExit(0 if not failed else 1)
