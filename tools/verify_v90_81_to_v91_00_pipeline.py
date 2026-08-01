from pathlib import Path
import argparse,hashlib,json
def h(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");a=p.parse_args()
o=Path(a.repository_root).resolve()/"release/v91_00/output";c=json.loads((o/"final_paper_automation_certificate_v91_00.json").read_text());v=json.loads((o/"final_paper_automation_verify_v91_00.json").read_text());u=dict(c);e=u.pop("certificate_sha256");s=c["summary"]
checks={"certificate_hash_valid":e==h(u),"status_pass":c["status"]=="PASS","verify_flag_true":v["verified"] is True,
"certificate_count_four":s["certificate_count"]==4,"acceptance_pass":s["acceptance_status"]=="PASS","audit_pass":s["audit_status"]=="PASS",
"final_complete":c["final_paper_automation_certification_complete"] is True,"rc1_ready":c["paper_automation_final_rc1_ready"] is True,
"contract_verified":c["end_to_end_contract_verified"] is True,"safety_verified":c["safety_matrix_verified"] is True,
"replay_verified":c["deterministic_replay_verified"] is True,"containment_verified":c["failure_containment_verified"] is True,
"rollback_verified":c["final_rollback_verified"] is True,"acceptance_verified":c["final_release_acceptance_verified"] is True,
"scheduler_disabled":c["scheduler_enabled"] is False,"runtime_disabled":c["runtime_loop_enabled"] is False,
"write_zero":c["write_capability_count"]==0,"network_zero":c["network_requests_executed"]==0,"orders_zero":c["actual_orders_submitted"]==0}
f=[k for k,x in checks.items() if not x]
print(json.dumps({"stage_range":"V90.81-V91.00","status":"PASS" if not f else "FAIL","release_candidate":c["release_candidate"],"checks":checks,"failed_checks":f,"next_phase":c["next_phase"]},indent=2,sort_keys=True));raise SystemExit(0 if not f else 1)
