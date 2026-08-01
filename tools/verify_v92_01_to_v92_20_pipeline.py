from pathlib import Path
import argparse,hashlib,json
def h(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");a=p.parse_args()
o=Path(a.repository_root).resolve()/"release/v92_20/output";c=json.loads((o/"actual_paper_dryrun_certificate_v92_20.json").read_text());v=json.loads((o/"actual_paper_dryrun_verify_v92_20.json").read_text());u=dict(c);e=u.pop("certificate_sha256");s=c["summary"]
checks={"certificate_hash_valid":e==h(u),"status_pass":c["status"]=="PASS","verify_flag_true":v["verified"] is True,
"client_order_id_present":bool(s["client_order_id"]),"idempotency_present":bool(s["idempotency_key"]),
"mock_accepted":s["mock_order_status"]=="accepted","fill_simulated":s["simulated_fill_status"]=="filled",
"reconciliation_pass":s["reconciliation_status"]=="PASS","transitions_five":s["transition_count"]==5,
"audit_pass":s["audit_status"]=="PASS","validation_complete":c["actual_paper_order_submission_dry_run_validation_complete"] is True,
"engine_ready":c["dry_run_order_engine_ready"] is True,"idempotency_verified":c["idempotency_verified"] is True,
"retry_blocked":c["retry_block_verified"] is True,"paper_submit_disabled":c["paper_order_submission_authorized"] is False,
"write_zero":c["write_capability_count"]==0,"network_zero":c["network_requests_executed"]==0,
"orders_zero":c["actual_orders_submitted"]==0}
f=[k for k,x in checks.items() if not x]
print(json.dumps({"stage_range":"V92.01-V92.20","status":"PASS" if not f else "FAIL","checks":checks,"failed_checks":f,"next_phase":c["next_phase"]},indent=2,sort_keys=True));raise SystemExit(0 if not f else 1)
