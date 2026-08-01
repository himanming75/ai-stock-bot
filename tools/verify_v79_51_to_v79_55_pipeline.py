from pathlib import Path
import argparse,hashlib,json
def d(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");a=p.parse_args();o=Path(a.repository_root).resolve()/"release/v79_55/output";cp=o/"historical_dataset_recovery_certificate_v79_55.json";vp=o/"historical_dataset_recovery_verify_v79_55.json";mp=o/"dataset_recovery_manifest_v79_54.json";lp=o/"dataset_recovery_execution_ledger.json"
 for x in (cp,vp,mp,lp):
  if not x.is_file():raise SystemExit(f"VERIFY FAIL: missing {x}")
 c=json.loads(cp.read_text());v=json.loads(vp.read_text());m=json.loads(mp.read_text());l=json.loads(lp.read_text());u=dict(c);e=u.pop("certificate_sha256",None)
 checks={"certificate_status_pass":c.get("status")=="PASS","certificate_hash_valid":e==d(u),"verify_status_pass":v.get("status")=="PASS","verify_flag_true":v.get("verified") is True,"manifest_stage_v79_54":m.get("stage")=="V79.54","active_version_selected":c.get("checks",{}).get("active_version_selected") is True,"source_validation_pass":c.get("checks",{}).get("source_validation_pass") is True,"source_preserved":l.get("source_versions_preserved") is True,"network_requests_zero":c.get("network_requests_executed")==0,"credentials_unused":c.get("credentials_used")==0,"trading_client_not_created":c.get("trading_client_created") is False,"actual_orders_zero":c.get("actual_orders_submitted")==0,"live_trading_not_authorized":c.get("live_trading_authorized") is False};f=[k for k,z in checks.items() if not z];print(json.dumps({"stage_range":"V79.51-V79.55","status":"PASS" if not f else "FAIL","checks":checks,"failed_checks":f,"next_phase":c.get("next_phase")},indent=2,sort_keys=True));return 0 if not f else 1
if __name__=="__main__":raise SystemExit(main())
