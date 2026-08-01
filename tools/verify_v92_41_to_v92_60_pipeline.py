from pathlib import Path
import argparse,hashlib,json
def h(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");a=p.parse_args()
o=Path(a.repository_root).resolve()/"release/v92_60/output";c=json.loads((o/"actual_paper_final_submission_certificate_v92_60.json").read_text());v=json.loads((o/"actual_paper_final_submission_verify_v92_60.json").read_text());u=dict(c);e=u.pop("certificate_sha256");s=c["summary"]
checks={"certificate_hash_valid":e==h(u),"status_pass":c["status"]=="PASS","verify_flag_true":v["verified"] is True,
"contract_pass":s["contract_status"]=="PASS","risk_pass":s["risk_status"]=="PASS",
"replay_pass":s["replay_status"]=="PASS","recovery_pass":s["recovery_status"]=="PASS",
"recovery_scenarios_five":s["recovery_scenario_count"]==5,
"rollback_pass":s["rollback_status"]=="PASS","tamper_pass":s["tamper_status"]=="PASS",
"acceptance_pass":s["acceptance_status"]=="PASS","audit_pass":s["audit_status"]=="PASS",
"cert_complete":c["actual_paper_final_submission_certification_complete"] is True,
"preview_rc_ready":c["actual_paper_final_submission_preview_rc1_ready"] is True,
"paper_submit_disabled":c["paper_order_submission_authorized"] is False,
"write_zero":c["write_capability_count"]==0,"network_zero":c["network_requests_executed"]==0,
"orders_zero":c["actual_orders_submitted"]==0}
f=[k for k,x in checks.items() if not x]
print(json.dumps({"stage_range":"V92.41-V92.60","status":"PASS" if not f else "FAIL",
"release_candidate":c["release_candidate"],"checks":checks,"failed_checks":f,
"next_phase":c["next_phase"]},indent=2,sort_keys=True))
raise SystemExit(0 if not f else 1)
