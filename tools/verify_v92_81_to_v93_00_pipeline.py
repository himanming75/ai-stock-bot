from pathlib import Path
import argparse,hashlib,json
def h(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");a=p.parse_args()
o=Path(a.repository_root).resolve()/"release/v93_00/output"
c=json.loads((o/"actual_paper_submission_rc_certificate_v93_00.json").read_text())
v=json.loads((o/"actual_paper_submission_rc_verify_v93_00.json").read_text())
u=dict(c);e=u.pop("certificate_sha256");s=c["summary"]
checks={"certificate_hash_valid":e==h(u),"status_pass":c["status"]=="PASS",
"verify_flag_true":v["verified"] is True,"manifest_pass":s["manifest_status"]=="PASS",
"readiness_pass":s["readiness_status"]=="PASS","lock_pass":s["lock_status"]=="PASS",
"acceptance_pass":s["acceptance_status"]=="PASS","rollback_pass":s["rollback_status"]=="PASS",
"archive_pass":s["archive_status"]=="PASS","archive_records_seven":s["archive_record_count"]==7,
"tamper_pass":s["tamper_status"]=="PASS","audit_pass":s["audit_status"]=="PASS",
"rc_complete":c["actual_paper_submission_release_candidate_complete"] is True,
"rc_ready":c["actual_paper_submission_preview_rc1_ready"] is True,
"paper_submit_disabled":c["paper_order_submission_authorized"] is False,
"write_zero":c["write_capability_count"]==0,"network_zero":c["network_requests_executed"]==0,
"orders_zero":c["actual_orders_submitted"]==0}
f=[k for k,x in checks.items() if not x]
print(json.dumps({"stage_range":"V92.81-V93.00","status":"PASS" if not f else "FAIL",
"release_candidate":c["release_candidate"],"checks":checks,"failed_checks":f,
"next_phase":c["next_phase"]},indent=2,sort_keys=True))
raise SystemExit(0 if not f else 1)
