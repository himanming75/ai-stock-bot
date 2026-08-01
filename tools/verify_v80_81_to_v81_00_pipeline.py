from pathlib import Path
import argparse,hashlib,json
def h(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");a=p.parse_args();o=Path(a.repository_root).resolve()/"release/v81_00/output"
 cp=o/"strategy_selection_certificate_v81_00.json";vp=o/"strategy_selection_verify_v81_00.json";mp=o/"strategy_selection_manifest_v80_91.json"
 for x in (cp,vp,mp):
  if not x.is_file():raise SystemExit(f"VERIFY FAIL: missing {x}")
 c=json.loads(cp.read_text());v=json.loads(vp.read_text());m=json.loads(mp.read_text());u=dict(c);e=u.pop("certificate_sha256",None);s=c.get("selection_summary",{})
 checks={"certificate_status_pass":c.get("status")=="PASS","certificate_hash_valid":e==h(u),"verify_flag_true":v.get("verified") is True,
 "manifest_stage_v80_91":m.get("stage")=="V80.91","strategy_count_four":s.get("strategy_count")==4,
 "backtest_count_sixteen":s.get("backtest_count")==16,"eligible_positive":s.get("eligible_strategy_count",0)>0,
 "champion_present":bool(s.get("champion_strategy_id")),"promotion_unauthorized":s.get("promotion_authorized") is False,
 "selection_complete":c.get("strategy_selection_complete") is True,"actual_orders_zero":c.get("actual_orders_submitted")==0,
 "paper_not_authorized":c.get("paper_trading_authorized") is False,"live_not_authorized":c.get("live_trading_authorized") is False}
 f=[k for k,z in checks.items() if not z];print(json.dumps({"stage_range":"V80.81-V81.00","status":"PASS" if not f else "FAIL","checks":checks,"failed_checks":f,"next_phase":c.get("next_phase")},indent=2,sort_keys=True));return 0 if not f else 1
if __name__=="__main__":raise SystemExit(main())
