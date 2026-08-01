from pathlib import Path
import argparse,json,hashlib
def h(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");a=p.parse_args()
 o=Path(a.repository_root).resolve()/"release/v88_60/output"
 c=json.loads((o/"market_data_operations_certificate_v88_60.json").read_text())
 v=json.loads((o/"market_data_operations_verify_v88_60.json").read_text())
 u=dict(c);e=u.pop("certificate_sha256");s=c["market_data_operations_summary"]
 checks={"certificate_hash_valid":e==h(u),"status_pass":c["status"]=="PASS",
 "verify_flag_true":v["verified"] is True,"schema_pass":s["schema_status"]=="PASS",
 "freshness_pass":s["freshness_status"]=="PASS","missing_pass":s["missing_status"]=="PASS",
 "duplicate_pass":s["duplicate_status"]=="PASS","ordering_pass":s["ordering_status"]=="PASS",
 "clock_pass":s["clock_status"]=="PASS","symbol_pass":s["symbol_status"]=="PASS",
 "provider_pass":s["provider_status"]=="PASS","fallback_pass":s["fallback_status"]=="PASS",
 "classification_clean":s["classification_status"]=="CLEAN",
 "negative_scenarios_pass":s["negative_scenarios_status"]=="PASS",
 "audit_pass":s["audit_status"]=="PASS",
 "foundation_complete":c["paper_market_data_operations_foundation_complete"] is True,
 "preview_ready":c["market_data_quality_preview_ready"] is True,
 "network_disabled":c["market_data_network_enabled"] is False,
 "network_zero":c["network_requests_executed"]==0,"orders_zero":c["actual_orders_submitted"]==0}
 f=[k for k,v in checks.items() if not v]
 print(json.dumps({"stage_range":"V88.41-V88.60","status":"PASS" if not f else "FAIL",
 "checks":checks,"failed_checks":f,"next_phase":c["next_phase"]},indent=2,sort_keys=True))
 return 0 if not f else 1
if __name__=="__main__":raise SystemExit(main())
