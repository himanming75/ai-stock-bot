from pathlib import Path
import argparse,hashlib,json,math
def h(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");a=p.parse_args();o=Path(a.repository_root).resolve()/"release/v82_00/output"
 cp=o/"paper_performance_certificate_v82_00.json";vp=o/"paper_performance_verify_v82_00.json";mp=o/"paper_performance_manifest_v81_92.json"
 for x in (cp,vp,mp):
  if not x.is_file():raise SystemExit(f"VERIFY FAIL: missing {x}")
 c=json.loads(cp.read_text());v=json.loads(vp.read_text());m=json.loads(mp.read_text());u=dict(c);e=u.pop("certificate_sha256",None);s=c.get("performance_summary",{})
 checks={"certificate_status_pass":c.get("status")=="PASS","certificate_hash_valid":e==h(u),"verify_flag_true":v.get("verified") is True,
 "manifest_stage_v81_92":m.get("stage")=="V81.92","observations_sufficient":s.get("observation_count",0)>=5,
 "trade_count_positive":s.get("trade_count",0)>0,"metrics_finite":all(math.isfinite(float(s.get(k,0))) for k in ("total_return","annualized_return","max_drawdown_pct","sharpe_ratio","sortino_ratio","profit_factor","win_rate","expectancy","calmar_ratio")),
 "risk_gate_pass":s.get("risk_gate_status")=="PASS","scorecard_certifiable":s.get("scorecard_rating")=="CERTIFIABLE",
 "audit_pass":s.get("audit_status")=="PASS","analytics_complete":c.get("paper_performance_analytics_complete") is True,
 "paper_framework_certified":c.get("paper_framework_certified") is True,"actual_orders_zero":c.get("actual_orders_submitted")==0,
 "paper_not_authorized":c.get("paper_trading_authorized") is False,"live_not_authorized":c.get("live_trading_authorized") is False}
 f=[k for k,z in checks.items() if not z];print(json.dumps({"stage_range":"V81.81-V82.00","status":"PASS" if not f else "FAIL","checks":checks,"failed_checks":f,"next_phase":c.get("next_phase")},indent=2,sort_keys=True));return 0 if not f else 1
if __name__=="__main__":raise SystemExit(main())
