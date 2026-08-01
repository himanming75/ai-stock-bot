from pathlib import Path
import argparse,hashlib,json
def h(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");a=p.parse_args();o=Path(a.repository_root).resolve()/"release/v80_40/output"
 cp=o/"paper_order_fill_engine_certificate_v80_40.json";vp=o/"paper_order_fill_engine_verify_v80_40.json";mp=o/"paper_order_fill_manifest_v80_37.json"
 for x in (cp,vp,mp):
  if not x.is_file():raise SystemExit(f"VERIFY FAIL: missing {x}")
 c=json.loads(cp.read_text());v=json.loads(vp.read_text());m=json.loads(mp.read_text());u=dict(c);e=u.pop("certificate_sha256",None);s=c.get("engine_summary",{})
 checks={"certificate_status_pass":c.get("status")=="PASS","certificate_hash_valid":e==h(u),"verify_flag_true":v.get("verified") is True,
 "manifest_stage_v80_37":m.get("stage")=="V80.37","orders_positive":s.get("order_count",0)>0,"fills_positive":s.get("fill_count",0)>0,
 "cancel_one":s.get("canceled_order_count")==1,"reject_one":s.get("rejected_order_count")==1,"positions_flat":s.get("position_count")==0,
 "actual_orders_zero":c.get("actual_orders_submitted")==0,"paper_not_authorized":c.get("paper_trading_authorized") is False,
 "live_not_authorized":c.get("live_trading_authorized") is False}
 f=[k for k,z in checks.items() if not z];print(json.dumps({"stage_range":"V80.21-V80.40","status":"PASS" if not f else "FAIL","checks":checks,"failed_checks":f,"next_phase":c.get("next_phase")},indent=2,sort_keys=True));return 0 if not f else 1
if __name__=="__main__":raise SystemExit(main())
