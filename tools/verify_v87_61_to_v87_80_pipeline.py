from pathlib import Path
import argparse,json,hashlib
def h(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");a=p.parse_args()
 o=Path(a.repository_root).resolve()/"release/v87_80/output"
 c=json.loads((o/"strategy_execution_final_certificate_v87_80.json").read_text())
 v=json.loads((o/"strategy_execution_final_verify_v87_80.json").read_text())
 u=dict(c);e=u.pop("certificate_sha256");s=c["strategy_execution_final_summary"]
 checks={"certificate_hash_valid":e==h(u),"status_pass":c["status"]=="PASS",
 "verify_flag_true":v["verified"] is True,
 "certificate_count_three":s["certificate_count"]==3,
 "audit_pass":s["audit_status"]=="PASS",
 "verification_pass":s["verification_status"]=="PASS",
 "release_package_pass":s["release_package_status"]=="PASS",
 "release_candidate_valid":s["release_candidate"]=="PAPER_STRATEGY_EXECUTION_RC1",
 "final_complete":c["paper_strategy_execution_final_certification_complete"] is True,
 "rc1_ready":c["paper_strategy_execution_rc1_ready"] is True,
 "network_zero":c["network_requests_executed"]==0,"orders_zero":c["actual_orders_submitted"]==0}
 f=[k for k,v in checks.items() if not v]
 print(json.dumps({"stage_range":"V87.61-V87.80","status":"PASS" if not f else "FAIL",
 "checks":checks,"failed_checks":f,"release_candidate":s["release_candidate"],
 "next_phase":c["next_phase"]},indent=2,sort_keys=True))
 return 0 if not f else 1
if __name__=="__main__":raise SystemExit(main())
