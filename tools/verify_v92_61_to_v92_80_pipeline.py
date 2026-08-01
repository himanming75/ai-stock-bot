from pathlib import Path
import argparse,hashlib,json
def h(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");a=p.parse_args()
o=Path(a.repository_root).resolve()/"release/v92_80/output";c=json.loads((o/"actual_paper_e2e_certificate_v92_80.json").read_text());v=json.loads((o/"actual_paper_e2e_verify_v92_80.json").read_text());u=dict(c);e=u.pop("certificate_sha256");s=c["summary"]
checks={"certificate_hash_valid":e==h(u),"status_pass":c["status"]=="PASS","verify_flag_true":v["verified"] is True,
"chain_four":s["certificate_count"]==4,"transitions_eleven":s["transition_count"]==11,
"idempotency_pass":s["idempotency_status"]=="PASS","reconciliation_pass":s["reconciliation_status"]=="PASS",
"containment_pass":s["containment_status"]=="PASS","failure_scenarios_six":s["failure_scenario_count"]==6,
"rollback_pass":s["rollback_status"]=="PASS","tamper_pass":s["tamper_status"]=="PASS",
"acceptance_pass":s["acceptance_status"]=="PASS","audit_pass":s["audit_status"]=="PASS",
"cert_complete":c["actual_paper_end_to_end_submission_certification_complete"] is True,
"e2e_ready":c["actual_paper_e2e_submission_preview_rc1_ready"] is True,
"paper_submit_disabled":c["paper_order_submission_authorized"] is False,
"write_zero":c["write_capability_count"]==0,"network_zero":c["network_requests_executed"]==0,
"orders_zero":c["actual_orders_submitted"]==0}
f=[k for k,x in checks.items() if not x]
print(json.dumps({"stage_range":"V92.61-V92.80","status":"PASS" if not f else "FAIL",
"release_candidate":c["release_candidate"],"checks":checks,"failed_checks":f,
"next_phase":c["next_phase"]},indent=2,sort_keys=True))
raise SystemExit(0 if not f else 1)
