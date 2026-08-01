from pathlib import Path
import argparse,json,hashlib
def h(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");a=p.parse_args()
 o=Path(a.repository_root).resolve()/"release/v88_40/output"
 c=json.loads((o/"runtime_loop_certificate_v88_40.json").read_text())
 v=json.loads((o/"runtime_loop_verify_v88_40.json").read_text())
 u=dict(c);e=u.pop("certificate_sha256");s=c["runtime_loop_summary"]
 checks={"certificate_hash_valid":e==h(u),"status_pass":c["status"]=="PASS",
 "verify_flag_true":v["verified"] is True,"market_open":s["market_status"]=="OPEN",
 "heartbeat_pass":s["heartbeat_status"]=="PASS","freshness_pass":s["freshness_status"]=="PASS",
 "cycle_pass":s["cycle_status"]=="PASS","signal_candidate":s["signal_status"]=="CANDIDATE",
 "queue_depth_one":s["queue_depth"]==1,"checkpoint_saved":s["checkpoint_status"]=="SAVED",
 "resume_preview_only":s["resume_status"]=="RESUMED_PREVIEW_ONLY",
 "shutdown_stopped":s["shutdown_status"]=="STOPPED",
 "retry_initial_allowed":s["retry_initial_allowed"],
 "retry_exhausted_blocked":s["retry_exhausted_blocked"],
 "negative_scenarios_pass":s["negative_scenarios_status"]=="PASS",
 "audit_pass":s["audit_status"]=="PASS",
 "foundation_complete":c["paper_strategy_runtime_loop_foundation_complete"] is True,
 "preview_ready":c["runtime_loop_preview_ready"] is True,
 "runtime_disabled":c["runtime_loop_enabled"] is False,
 "network_zero":c["network_requests_executed"]==0,"orders_zero":c["actual_orders_submitted"]==0}
 f=[k for k,v in checks.items() if not v]
 print(json.dumps({"stage_range":"V88.21-V88.40","status":"PASS" if not f else "FAIL",
 "checks":checks,"failed_checks":f,"next_phase":c["next_phase"]},indent=2,sort_keys=True))
 return 0 if not f else 1
if __name__=="__main__":raise SystemExit(main())
