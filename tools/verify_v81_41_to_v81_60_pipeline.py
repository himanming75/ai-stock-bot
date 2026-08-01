from pathlib import Path
import argparse,hashlib,json
def h(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");a=p.parse_args();out=Path(a.repository_root).resolve()/"release/v81_60/output"
 cp=out/"broker_adapter_foundation_certificate_v81_60.json";vp=out/"broker_adapter_foundation_verify_v81_60.json";mp=out/"broker_adapter_manifest_v81_56.json"
 for x in (cp,vp,mp):
  if not x.is_file():raise SystemExit(f"VERIFY FAIL: missing {x}")
 c=json.loads(cp.read_text());v=json.loads(vp.read_text());m=json.loads(mp.read_text());u=dict(c);e=u.pop("certificate_sha256",None);s=c.get("adapter_summary",{})
 checks={"certificate_status_pass":c.get("status")=="PASS","certificate_hash_valid":e==h(u),"verify_flag_true":v.get("verified") is True,
 "manifest_stage_v81_56":m.get("stage")=="V81.56","adapter_count_three":s.get("adapter_count")==3,
 "selected_adapter_sandbox":s.get("selected_adapter")=="SANDBOX_BROKER","preview_count_one":s.get("order_preview_count")==1,
 "audit_pass":s.get("audit_status")=="PASS","foundation_complete":c.get("broker_adapter_foundation_complete") is True,
 "actual_orders_zero":c.get("actual_orders_submitted")==0,"network_zero":c.get("network_requests_executed")==0,
 "credentials_zero":c.get("credentials_used")==0,"client_false":c.get("trading_client_created") is False,
 "paper_not_authorized":c.get("paper_trading_authorized") is False,"live_not_authorized":c.get("live_trading_authorized") is False}
 failed=[k for k,z in checks.items() if not z];print(json.dumps({"stage_range":"V81.41-V81.60","status":"PASS" if not failed else "FAIL","checks":checks,"failed_checks":failed,"next_phase":c.get("next_phase")},indent=2,sort_keys=True));return 0 if not failed else 1
if __name__=="__main__":raise SystemExit(main())
