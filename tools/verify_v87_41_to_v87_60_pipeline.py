from pathlib import Path
import argparse,json,hashlib
def h(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");a=p.parse_args()
 o=Path(a.repository_root).resolve()/"release/v87_60/output"
 c=json.loads((o/"strategy_execution_recon_certificate_v87_60.json").read_text())
 v=json.loads((o/"strategy_execution_recon_verify_v87_60.json").read_text())
 u=dict(c);e=u.pop("certificate_sha256");s=c["strategy_execution_reconciliation_summary"]
 checks={"certificate_hash_valid":e==h(u),"status_pass":c["status"]=="PASS",
 "verify_flag_true":v["verified"] is True,
 "order_fill_pass":s["order_fill_status"]=="PASS","quantity_pass":s["quantity_status"]=="PASS",
 "cash_pass":s["cash_status"]=="PASS","equity_pass":s["equity_status"]=="PASS",
 "pnl_pass":s["pnl_status"]=="PASS","drawdown_pass":s["drawdown_status"]=="PASS",
 "budget_pass":s["budget_status"]=="PASS","replay_pass":s["replay_status"]=="PASS",
 "tamper_pass":s["tamper_status"]=="PASS","rollback_pass":s["rollback_status"]=="PASS",
 "audit_pass":s["audit_status"]=="PASS",
 "reconciliation_complete":c["paper_strategy_execution_reconciliation_complete"] is True,
 "chain_certified":c["strategy_execution_chain_certified"] is True,
 "network_zero":c["network_requests_executed"]==0,"orders_zero":c["actual_orders_submitted"]==0}
 f=[k for k,v in checks.items() if not v]
 print(json.dumps({"stage_range":"V87.41-V87.60","status":"PASS" if not f else "FAIL",
 "checks":checks,"failed_checks":f,"next_phase":c["next_phase"]},indent=2,sort_keys=True))
 return 0 if not f else 1
if __name__=="__main__":raise SystemExit(main())
