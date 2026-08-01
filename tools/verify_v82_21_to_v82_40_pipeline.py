from pathlib import Path
import argparse,hashlib,json
def h(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");a=p.parse_args();o=Path(a.repository_root).resolve()/"release/v82_40/output"
 cp=o/"broker_read_only_foundation_certificate_v82_40.json";vp=o/"broker_read_only_foundation_verify_v82_40.json";mp=o/"broker_read_only_manifest_v82_38.json"
 for x in (cp,vp,mp):
  if not x.is_file():raise SystemExit(f"VERIFY FAIL: missing {x}")
 c=json.loads(cp.read_text());v=json.loads(vp.read_text());m=json.loads(mp.read_text());u=dict(c);e=u.pop("certificate_sha256",None);s=c.get("broker_read_only_summary",{})
 checks={"certificate_status_pass":c.get("status")=="PASS","certificate_hash_valid":e==h(u),"verify_flag_true":v.get("verified") is True,
 "manifest_stage_v82_38":m.get("stage")=="V82.38","read_capabilities_positive":s.get("read_capability_count",0)>0,
 "write_capabilities_zero":s.get("write_capability_count")==0,"account_one":s.get("account_count")==1,
 "positions_positive":s.get("position_count",0)>0,"orders_positive":s.get("order_count",0)>0,
 "sync_health_pass":s.get("sync_health_status")=="PASS","audit_pass":s.get("audit_status")=="PASS",
 "foundation_complete":c.get("broker_read_only_foundation_complete") is True,"actual_orders_zero":c.get("actual_orders_submitted")==0,
 "paper_not_authorized":c.get("paper_trading_authorized") is False,"live_not_authorized":c.get("live_trading_authorized") is False}
 f=[k for k,z in checks.items() if not z];print(json.dumps({"stage_range":"V82.21-V82.40","status":"PASS" if not f else "FAIL","checks":checks,"failed_checks":f,"next_phase":c.get("next_phase")},indent=2,sort_keys=True));return 0 if not f else 1
if __name__=="__main__":raise SystemExit(main())
