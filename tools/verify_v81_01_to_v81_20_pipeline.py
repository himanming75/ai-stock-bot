from pathlib import Path
import argparse,hashlib,json
def h(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");a=p.parse_args();o=Path(a.repository_root).resolve()/"release/v81_20/output"
 cp=o/"portfolio_optimization_certificate_v81_20.json";vp=o/"portfolio_optimization_verify_v81_20.json";mp=o/"portfolio_optimization_manifest_v81_17.json"
 for x in (cp,vp,mp):
  if not x.is_file():raise SystemExit(f"VERIFY FAIL: missing {x}")
 c=json.loads(cp.read_text());v=json.loads(vp.read_text());m=json.loads(mp.read_text());u=dict(c);e=u.pop("certificate_sha256",None);s=c.get("optimization_summary",{})
 checks={"certificate_status_pass":c.get("status")=="PASS","certificate_hash_valid":e==h(u),"verify_flag_true":v.get("verified") is True,
 "manifest_stage_v81_17":m.get("stage")=="V81.17","strategy_count_four":s.get("strategy_count")==4,
 "candidate_count_five":s.get("candidate_count")==5,"eligible_positive":s.get("eligible_candidate_count",0)>0,
 "weight_sum_valid":abs(s.get("weight_sum",0)-.9)<1e-8,"order_quantity_zero":s.get("order_quantity")==0,
 "optimization_complete":c.get("portfolio_optimization_complete") is True,"actual_orders_zero":c.get("actual_orders_submitted")==0,
 "paper_not_authorized":c.get("paper_trading_authorized") is False,"live_not_authorized":c.get("live_trading_authorized") is False}
 f=[k for k,z in checks.items() if not z];print(json.dumps({"stage_range":"V81.01-V81.20","status":"PASS" if not f else "FAIL","checks":checks,"failed_checks":f,"next_phase":c.get("next_phase")},indent=2,sort_keys=True));return 0 if not f else 1
if __name__=="__main__":raise SystemExit(main())
