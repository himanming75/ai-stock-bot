from pathlib import Path
import argparse,hashlib,json
def h(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");a=p.parse_args()
o=Path(a.repository_root).resolve()/"release/v95_00/output"
c=json.loads((o/"single_order_network_optin_certificate_v95_00.json").read_text())
v=json.loads((o/"single_order_network_optin_verify_v95_00.json").read_text())
u=dict(c);e=u.pop("certificate_sha256");s=c["summary"]
checks={"certificate_hash_valid":e==h(u),"status_pass":c["status"]=="PASS",
"verify_flag_true":v["verified"] is True,"paper_url":s["base_url"]=="https://paper-api.alpaca.markets",
"single_order":s["max_orders_per_session"]==1,"notional_100":s["max_order_notional"]==100.0,
"quantity_one":s["max_quantity"]==1,"request_preview_ready":s["request_preview_status"]=="READY_PREVIEW_ONLY",
"parser_pass":s["response_parser_status"]=="PASS","failure_scenarios_six":s["failure_scenario_count"]==6,
"reconciliation_pass":s["reconciliation_status"]=="PASS","safety_pass":s["safety_status"]=="PASS",
"fast_track_complete":c["single_order_network_opt_in_fast_track_complete"] is True,
"network_ready_rc1":c["actual_paper_single_order_network_ready_rc1"] is True,
"paper_submit_disabled":c["paper_order_submission_authorized"] is False,
"write_zero":c["write_capability_count"]==0,"network_zero":c["network_requests_executed"]==0,
"orders_zero":c["actual_orders_submitted"]==0}
f=[k for k,x in checks.items() if not x]
print(json.dumps({"stage_range":"V94.01-V95.00","status":"PASS" if not f else "FAIL",
"release_candidate":c["release_candidate"],"checks":checks,"failed_checks":f,
"next_phase":c["next_phase"]},indent=2,sort_keys=True))
raise SystemExit(0 if not f else 1)
