from pathlib import Path
import argparse,hashlib,json
def h(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");a=p.parse_args()
o=Path(a.repository_root).resolve()/"release/v96_00/output"
c=json.loads((o/"controlled_execution_certificate_v96_00.json").read_text())
v=json.loads((o/"controlled_execution_verify_v96_00.json").read_text())
u=dict(c);e=u.pop("certificate_sha256");s=c["summary"]
checks={"certificate_hash_valid":e==h(u),"status_pass":c["status"]=="PASS","verify_flag_true":v["verified"] is True,
"fixture_accepted":s["fixture_execution_status"]=="FIXTURE_ACCEPTED",
"reconciliation_pass":s["fixture_reconciliation_status"]=="PASS",
"failure_scenarios_seven":s["failure_scenario_count"]==7,
"rollback_pass":s["rollback_status"]=="PASS","default_safety_pass":s["default_safety_status"]=="PASS",
"notional_100":s["max_order_notional"]==100.0,"quantity_one":s["max_quantity"]==1,
"fast_track_complete":c["controlled_execution_fast_track_complete"] is True,
"controlled_rc_ready":c["actual_paper_single_order_controlled_rc1_ready"] is True,
"default_submit_disabled":c["default_paper_order_submission_authorized"] is False,
"default_network_zero":c["default_network_requests_executed"]==0,
"default_orders_zero":c["default_actual_orders_submitted"]==0}
f=[k for k,x in checks.items() if not x]
print(json.dumps({"stage_range":"V95.01-V96.00","status":"PASS" if not f else "FAIL",
"release_candidate":c["release_candidate"],"checks":checks,"failed_checks":f,
"next_phase":c["next_phase"]},indent=2,sort_keys=True))
raise SystemExit(0 if not f else 1)
