from pathlib import Path
import argparse,hashlib,json
def h(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");a=p.parse_args();o=Path(a.repository_root).resolve()/"release/v79_75/output"
 cp=o/"historical_signal_engine_certificate_v79_75.json";vp=o/"historical_signal_engine_verify_v79_75.json";mp=o/"historical_signal_manifest_v79_74.json"
 for x in (cp,vp,mp):
  if not x.is_file():raise SystemExit(f"VERIFY FAIL: missing {x}")
 c=json.loads(cp.read_text());v=json.loads(vp.read_text());m=json.loads(mp.read_text());u=dict(c);e=u.pop("certificate_sha256",None)
 checks={"certificate_status_pass":c.get("status")=="PASS","certificate_hash_valid":e==h(u),"verify_flag_true":v.get("verified") is True,"manifest_stage_v79_74":m.get("stage")=="V79.74","signal_rows_positive":c.get("signal_summary",{}).get("signal_row_count",0)>0,"distribution_complete":sum(c.get("signal_summary",{}).get(x,0) for x in ("buy_count","sell_count","hold_count"))==c.get("signal_summary",{}).get("signal_row_count"),"actual_orders_zero":c.get("actual_orders_submitted")==0}
 f=[k for k,z in checks.items() if not z];print(json.dumps({"stage_range":"V79.71-V79.75","status":"PASS" if not f else "FAIL","checks":checks,"failed_checks":f,"next_phase":c.get("next_phase")},indent=2));return 0 if not f else 1
if __name__=="__main__":raise SystemExit(main())
