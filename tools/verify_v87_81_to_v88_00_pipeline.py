from pathlib import Path
import argparse,json,hashlib
def h(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");a=p.parse_args()
 o=Path(a.repository_root).resolve()/"release/v88_00/output"
 c=json.loads((o/"strategy_operations_rc_certificate_v88_00.json").read_text())
 v=json.loads((o/"strategy_operations_rc_verify_v88_00.json").read_text())
 u=dict(c);e=u.pop("certificate_sha256");s=c["strategy_operations_rc_summary"]
 checks={"certificate_hash_valid":e==h(u),"status_pass":c["status"]=="PASS",
 "verify_flag_true":v["verified"] is True,
 "startup_pass":s["startup_status"]=="PASS",
 "health_pass":s["health_status"]=="PASS",
 "scheduler_disabled":s["scheduler_enabled"] is False,
 "positive_limit_pass":s["positive_limit_status"]=="PASS",
 "negative_limit_fail":s["negative_limit_status"]=="FAIL",
 "incident_recovery_ready":s["incident_recovery_ready"],
 "daily_report_pass":s["daily_report_status"]=="PASS",
 "shutdown_stopped":s["shutdown_status"]=="STOPPED",
 "rollback_pass":s["rollback_status"]=="PASS",
 "audit_pass":s["audit_status"]=="PASS",
 "acceptance_pass":s["acceptance_status"]=="PASS",
 "operations_rc_complete":c["paper_strategy_operations_rc_complete"] is True,
 "operations_rc1_ready":c["paper_strategy_operations_rc1_ready"] is True,
 "network_zero":c["network_requests_executed"]==0,
 "orders_zero":c["actual_orders_submitted"]==0}
 f=[k for k,v in checks.items() if not v]
 print(json.dumps({"stage_range":"V87.81-V88.00","status":"PASS" if not f else "FAIL",
 "checks":checks,"failed_checks":f,"release_candidate":s["release_candidate"],
 "next_phase":c["next_phase"]},indent=2,sort_keys=True))
 return 0 if not f else 1
if __name__=="__main__":raise SystemExit(main())
