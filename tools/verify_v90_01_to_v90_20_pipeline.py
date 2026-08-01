from pathlib import Path
import argparse,json,hashlib
def h(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");a=p.parse_args()
o=Path(a.repository_root).resolve()/"release/v90_20/output"
c=json.loads((o/"actual_paper_automation_certificate_v90_20.json").read_text())
v=json.loads((o/"actual_paper_automation_verify_v90_20.json").read_text())
u=dict(c);e=u.pop("certificate_sha256")
s=c["summary"]
checks={"certificate_hash_valid":e==h(u),"status_pass":c["status"]=="PASS",
"verify_flag_true":v["verified"] is True,"endpoint_count_three":s["endpoint_count"]==3,
"read_capabilities_three":s["read_capability_count"]==3,"write_capabilities_zero":s["write_capability_count"]==0,
"account_pass":s["account_status"]=="PASS","clock_pass":s["clock_status"]=="PASS",
"calendar_pass":s["calendar_status"]=="PASS","audit_pass":s["audit_status"]=="PASS",
"foundation_complete":c["actual_paper_automation_enablement_foundation_complete"] is True,
"read_only_ready":c["actual_paper_read_only_ready"] is True,
"paper_submit_disabled":c["paper_order_submission_authorized"] is False,
"orders_zero":c["actual_orders_submitted"]==0}
failed=[k for k,x in checks.items() if not x]
print(json.dumps({"stage_range":"V90.01-V90.20","status":"PASS" if not failed else "FAIL",
"checks":checks,"failed_checks":failed,"next_phase":c["next_phase"]},indent=2,sort_keys=True))
raise SystemExit(0 if not failed else 1)
