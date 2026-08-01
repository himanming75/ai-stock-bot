from pathlib import Path
import argparse,json,hashlib
def h(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");a=p.parse_args()
 o=Path(a.repository_root).resolve()/"release/v87_20/output"
 c=json.loads((o/"strategy_execution_certificate_v87_20.json").read_text())
 v=json.loads((o/"strategy_execution_verify_v87_20.json").read_text())
 u=dict(c);e=u.pop("certificate_sha256");s=c["strategy_execution_summary"]
 checks={"certificate_hash_valid":e==h(u),"status_pass":c["status"]=="PASS",
 "verify_flag_true":v["verified"] is True,"signal_validation_pass":s["signal_validation_status"]=="PASS",
 "risk_pass":s["risk_status"]=="PASS","approval_approved":s["approval_status"]=="APPROVED",
 "preview_only":s["preview_status"]=="PREVIEW_ONLY","budget_reserved":s["reservation_status"]=="RESERVED",
 "context_ready":s["context_status"]=="READY_FOR_MANUAL_REVIEW",
 "checkpoint_resumable":s["checkpoint_resumable"],"session_resumed":s["session_resume_status"]=="RESUMED_PREVIEW_ONLY",
 "preview_canceled":s["preview_canceled"],"lock_released":s["strategy_lock_released"],
 "rejections_positive":s["rejection_count"]>=5,"rollback_pass":s["rollback_status"]=="PASS",
 "audit_pass":s["audit_status"]=="PASS","operations_complete":c["paper_strategy_execution_operations_complete"] is True,
 "preview_ready":c["strategy_execution_preview_ready"] is True,
 "network_zero":c["network_requests_executed"]==0,"orders_zero":c["actual_orders_submitted"]==0}
 f=[k for k,v in checks.items() if not v]
 print(json.dumps({"stage_range":"V87.01-V87.20","status":"PASS" if not f else "FAIL",
 "checks":checks,"failed_checks":f,"next_phase":c["next_phase"]},indent=2,sort_keys=True))
 return 0 if not f else 1
if __name__=="__main__":raise SystemExit(main())
