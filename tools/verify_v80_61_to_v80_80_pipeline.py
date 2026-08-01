from pathlib import Path
import argparse,hashlib,json
def h(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");a=p.parse_args();o=Path(a.repository_root).resolve()/"release/v80_80/output"
 cp=o/"strategy_engine_foundation_certificate_v80_80.json";vp=o/"strategy_engine_foundation_verify_v80_80.json";mp=o/"strategy_engine_manifest_v80_71.json"
 for x in (cp,vp,mp):
  if not x.is_file():raise SystemExit(f"VERIFY FAIL: missing {x}")
 c=json.loads(cp.read_text());v=json.loads(vp.read_text());m=json.loads(mp.read_text());u=dict(c);e=u.pop("certificate_sha256",None);s=c.get("strategy_summary",{})
 checks={"certificate_status_pass":c.get("status")=="PASS","certificate_hash_valid":e==h(u),"verify_flag_true":v.get("verified") is True,
 "manifest_stage_v80_71":m.get("stage")=="V80.71","strategy_count_four":s.get("strategy_count")==4,
 "signal_count_four":s.get("signal_count")==4,"order_quantity_zero":s.get("order_quantity")==0,
 "foundation_complete":c.get("strategy_engine_foundation_complete") is True,"actual_orders_zero":c.get("actual_orders_submitted")==0,
 "paper_not_authorized":c.get("paper_trading_authorized") is False,"live_not_authorized":c.get("live_trading_authorized") is False}
 f=[k for k,z in checks.items() if not z];print(json.dumps({"stage_range":"V80.61-V80.80","status":"PASS" if not f else "FAIL","checks":checks,"failed_checks":f,"next_phase":c.get("next_phase")},indent=2,sort_keys=True));return 0 if not f else 1
if __name__=="__main__":raise SystemExit(main())
