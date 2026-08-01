from pathlib import Path
import argparse,hashlib,json
def h(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");a=p.parse_args();o=Path(a.repository_root).resolve()/"release/v79_85/output"
 cp=o/"historical_risk_engine_certificate_v79_85.json";vp=o/"historical_risk_engine_verify_v79_85.json";mp=o/"historical_risk_manifest_v79_84.json"
 for x in (cp,vp,mp):
  if not x.is_file():raise SystemExit(f"VERIFY FAIL: missing {x}")
 c=json.loads(cp.read_text());v=json.loads(vp.read_text());m=json.loads(mp.read_text());u=dict(c);e=u.pop("certificate_sha256",None)
 checks={"certificate_status_pass":c.get("status")=="PASS","certificate_hash_valid":e==h(u),"verify_flag_true":v.get("verified") is True,
 "manifest_stage_v79_84":m.get("stage")=="V79.84","violations_zero":c.get("risk_summary",{}).get("violation_count")==0,
 "drawdown_within_limit":c.get("risk_summary",{}).get("max_drawdown_pct",1)<=c.get("config",{}).get("max_drawdown_pct",0),
 "actual_orders_zero":c.get("actual_orders_submitted")==0}
 f=[k for k,z in checks.items() if not z];print(json.dumps({"stage_range":"V79.81-V79.85","status":"PASS" if not f else "FAIL","checks":checks,"failed_checks":f,"next_phase":c.get("next_phase")},indent=2));return 0 if not f else 1
if __name__=="__main__":raise SystemExit(main())
