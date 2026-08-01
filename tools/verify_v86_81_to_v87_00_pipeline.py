from pathlib import Path
import argparse,json,hashlib
def h(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");a=p.parse_args()
 o=Path(a.repository_root).resolve()/"release/v87_00/output"
 c=json.loads((o/"operations_certificate_v87_00.json").read_text())
 v=json.loads((o/"operations_verify_v87_00.json").read_text())
 u=dict(c);e=u.pop("certificate_sha256");s=c["operations_summary"]
 checks={"certificate_hash_valid":e==h(u),"status_pass":c["status"]=="PASS",
 "verify_flag_true":v["verified"] is True,"manual_start_required":s["manual_start_required"],
 "manual_stop_required":s["manual_stop_required"],"daily_order_limit_one":s["daily_order_limit"]==1,
 "health_pass":s["health_status"]=="PASS","negative_limit_test_fail":s["limit_guard_negative_test"]=="FAIL",
 "incident_ready":s["incident_response_ready"],"rollback_pass":s["rollback_status"]=="PASS",
 "runbook_pass":s["runbook_status"]=="PASS","checklist_pass":s["checklist_status"]=="PASS",
 "audit_pass":s["audit_status"]=="PASS","operations_complete":c["paper_broker_operations_foundation_complete"] is True,
 "rc_ready":c["paper_broker_release_candidate_ready"] is True,
 "network_zero":c["network_requests_executed"]==0,"orders_zero":c["actual_orders_submitted"]==0}
 f=[k for k,v in checks.items() if not v]
 print(json.dumps({"stage_range":"V86.81-V87.00","status":"PASS" if not f else "FAIL",
 "checks":checks,"failed_checks":f,"release_candidate":s["release_candidate"],
 "next_phase":c["next_phase"]},indent=2,sort_keys=True))
 return 0 if not f else 1
if __name__=="__main__":raise SystemExit(main())
