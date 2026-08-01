from pathlib import Path
import argparse,json,hashlib
def h(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");a=p.parse_args()
 o=Path(a.repository_root).resolve()/"release/v88_20/output"
 c=json.loads((o/"scheduler_foundation_certificate_v88_20.json").read_text())
 v=json.loads((o/"scheduler_foundation_verify_v88_20.json").read_text())
 u=dict(c);e=u.pop("certificate_sha256");s=c["scheduler_foundation_summary"]
 checks={"certificate_hash_valid":e==h(u),"status_pass":c["status"]=="PASS",
 "verify_flag_true":v["verified"] is True,"normal_trading_day":s["normal_trading_day"],
 "holiday_closed":s["holiday_closed"],"early_close_detected":s["early_close_detected"],
 "dst_pass":s["dst_status"]=="PASS","event_count_four":s["event_count"]==4,
 "duplicate_detected":s["duplicate_detected"],"missed_recoverable":s["missed_recoverable"],
 "manual_override_approved":s["manual_override_approved"],
 "stale_heartbeat_detected":s["stale_heartbeat_detected"],
 "shutdown_pass":s["shutdown_status"]=="PASS","rollback_pass":s["rollback_status"]=="PASS",
 "audit_pass":s["audit_status"]=="PASS",
 "foundation_complete":c["paper_scheduler_foundation_complete"] is True,
 "preview_ready":c["scheduler_preview_ready"] is True,
 "scheduler_disabled":c["scheduler_enabled"] is False,
 "network_zero":c["network_requests_executed"]==0,"orders_zero":c["actual_orders_submitted"]==0}
 f=[k for k,v in checks.items() if not v]
 print(json.dumps({"stage_range":"V88.01-V88.20","status":"PASS" if not f else "FAIL",
 "checks":checks,"failed_checks":f,"next_phase":c["next_phase"]},indent=2,sort_keys=True))
 return 0 if not f else 1
if __name__=="__main__":raise SystemExit(main())
