from pathlib import Path
import argparse,hashlib,json
def h(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");a=p.parse_args()
o=Path(a.repository_root).resolve()/"release/v94_00/output"
c=json.loads((o/"submission_fast_track_certificate_v94_00.json").read_text())
v=json.loads((o/"submission_fast_track_verify_v94_00.json").read_text())
u=dict(c);e=u.pop("certificate_sha256");s=c["summary"]
checks={"certificate_hash_valid":e==h(u),"status_pass":c["status"]=="PASS","verify_flag_true":v["verified"] is True,
"approval_count_two":s["approval_count"]==2,"ttl_300":s["session_ttl_seconds"]==300,
"single_order":s["max_orders_per_session"]==1,"notional_100":s["max_order_notional"]==100.0,
"quantity_one":s["max_quantity"]==1,"preview_ready":s["preview_status"]=="READY_OFFLINE_PREVIEW",
"mock_pass":s["mock_status"]=="PASS","reconciliation_pass":s["reconciliation_status"]=="PASS",
"safety_pass":s["safety_status"]=="PASS","fast_track_complete":c["submission_enablement_fast_track_complete"] is True,
"rc_ready":c["single_order_preview_rc1_ready"] is True,
"paper_submit_disabled":c["paper_order_submission_authorized"] is False,
"write_zero":c["write_capability_count"]==0,"network_zero":c["network_requests_executed"]==0,
"orders_zero":c["actual_orders_submitted"]==0}
f=[k for k,x in checks.items() if not x]
print(json.dumps({"stage_range":"V93.01-V94.00","status":"PASS" if not f else "FAIL",
"release_candidate":c["release_candidate"],"checks":checks,"failed_checks":f,
"next_phase":c["next_phase"]},indent=2,sort_keys=True))
raise SystemExit(0 if not f else 1)
