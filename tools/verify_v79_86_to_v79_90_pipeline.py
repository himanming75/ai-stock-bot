from pathlib import Path
import argparse,hashlib,json,math
def h(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");a=p.parse_args();o=Path(a.repository_root).resolve()/"release/v79_90/output"
 cp=o/"historical_performance_analytics_certificate_v79_90.json";vp=o/"historical_performance_analytics_verify_v79_90.json";mp=o/"historical_performance_manifest_v79_89.json"
 for x in (cp,vp,mp):
  if not x.is_file():raise SystemExit(f"VERIFY FAIL: missing {x}")
 c=json.loads(cp.read_text());v=json.loads(vp.read_text());m=json.loads(mp.read_text());u=dict(c);e=u.pop("certificate_sha256",None)
 s=c.get("performance_summary",{})
 checks={"certificate_status_pass":c.get("status")=="PASS","certificate_hash_valid":e==h(u),"verify_flag_true":v.get("verified") is True,
 "manifest_stage_v79_89":m.get("stage")=="V79.89","metrics_finite":all(math.isfinite(float(s.get(k,0))) for k in ("total_return","annualized_return","sharpe_ratio","sortino_ratio","calmar_ratio","profit_factor","expectancy")),
 "actual_orders_zero":c.get("actual_orders_submitted")==0}
 f=[k for k,z in checks.items() if not z];print(json.dumps({"stage_range":"V79.86-V79.90","status":"PASS" if not f else "FAIL","checks":checks,"failed_checks":f,"next_phase":c.get("next_phase")},indent=2));return 0 if not f else 1
if __name__=="__main__":raise SystemExit(main())
