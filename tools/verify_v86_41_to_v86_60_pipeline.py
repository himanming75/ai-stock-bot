from pathlib import Path
import json,hashlib,argparse
def h(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");a=p.parse_args()
 o=Path(a.repository_root).resolve()/"release/v86_60/output"
 c=json.loads((o/"position_account_certificate_v86_60.json").read_text())
 v=json.loads((o/"position_account_verify_v86_60.json").read_text())
 u=dict(c);e=u.pop("certificate_sha256");s=c["position_account_summary"]
 checks={"certificate_hash_valid":e==h(u),"status_pass":c["status"]=="PASS",
 "verify_flag_true":v["verified"] is True,
 "quantity_pass":s["quantity_status"]=="PASS",
 "average_price_pass":s["average_price_status"]=="PASS",
 "market_value_pass":s["market_value_status"]=="PASS",
 "unrealized_pnl_pass":s["unrealized_pnl_status"]=="PASS",
 "account_pass":s["account_status"]=="PASS",
 "buying_power_pass":s["buying_power_status"]=="PASS",
 "validation_complete":c["paper_position_account_reconciliation_complete"] is True,
 "orders_zero":c["actual_orders_submitted"]==0}
 f=[k for k,v in checks.items() if not v]
 print(json.dumps({"stage_range":"V86.41-V86.60","status":"PASS" if not f else "FAIL",
 "checks":checks,"failed_checks":f,"network_mode":s["network_mode"],"next_phase":c["next_phase"]},indent=2,sort_keys=True))
 return 0 if not f else 1
if __name__=="__main__":raise SystemExit(main())
