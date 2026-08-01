from pathlib import Path
import argparse,hashlib,json
def h(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");a=p.parse_args();o=Path(a.repository_root).resolve()/"release/v81_40/output"
 cp=o/"multi_asset_portfolio_certificate_v81_40.json";vp=o/"multi_asset_portfolio_verify_v81_40.json";mp=o/"multi_asset_manifest_v81_36.json"
 for x in (cp,vp,mp):
  if not x.is_file():raise SystemExit(f"VERIFY FAIL: missing {x}")
 c=json.loads(cp.read_text());v=json.loads(vp.read_text());m=json.loads(mp.read_text());u=dict(c);e=u.pop("certificate_sha256",None);s=c.get("multi_asset_summary",{})
 checks={"certificate_status_pass":c.get("status")=="PASS","certificate_hash_valid":e==h(u),"verify_flag_true":v.get("verified") is True,
 "manifest_stage_v81_36":m.get("stage")=="V81.36","asset_count_six":s.get("asset_count")==6,
 "weight_sum_valid":abs(s.get("target_weight_sum",0)-.9)<1e-8,"turnover_within_limit":s.get("turnover",1)<=.35+1e-9,
 "gross_exposure_valid":abs(s.get("gross_exposure",0)-.9)<1e-8,"risk_budget_sum_valid":abs(s.get("risk_budget_sum",0)-1)<1e-8,
 "orders_zero":s.get("orders_created")==0,"multi_asset_complete":c.get("multi_asset_portfolio_complete") is True,
 "actual_orders_zero":c.get("actual_orders_submitted")==0,"paper_not_authorized":c.get("paper_trading_authorized") is False,
 "live_not_authorized":c.get("live_trading_authorized") is False}
 f=[k for k,z in checks.items() if not z];print(json.dumps({"stage_range":"V81.21-V81.40","status":"PASS" if not f else "FAIL","checks":checks,"failed_checks":f,"next_phase":c.get("next_phase")},indent=2,sort_keys=True));return 0 if not f else 1
if __name__=="__main__":raise SystemExit(main())
