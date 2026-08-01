from pathlib import Path
import argparse,hashlib,json
def h(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");a=p.parse_args();o=Path(a.repository_root).resolve()/"release/v83_20/output"
 cp=o/"paper_order_gate_certificate_v83_20.json";vp=o/"paper_order_gate_verify_v83_20.json";mp=o/"paper_order_gate_manifest_v83_19.json"
 for x in (cp,vp,mp):
  if not x.is_file():raise SystemExit(f"VERIFY FAIL: missing {x}")
 c=json.loads(cp.read_text());v=json.loads(vp.read_text());m=json.loads(mp.read_text());u=dict(c);e=u.pop("certificate_sha256",None);s=c.get("paper_order_gate_summary",{})
 checks={"certificate_status_pass":c.get("status")=="PASS","certificate_hash_valid":e==h(u),"verify_flag_true":v.get("verified") is True,
 "manifest_stage_v83_19":m.get("stage")=="V83.19","paper_session_authorized":s.get("paper_session_authorized") is True,
 "paper_submit_false":s.get("paper_order_submission_authorized") is False,"live_not_authorized":s.get("live_trading_authorized") is False,
 "scenario_count_four":s.get("scenario_count")==4,"gate_pass_positive":s.get("gate_pass_count",0)>0,
 "gate_reject_positive":s.get("gate_reject_count",0)>0,"duplicate_detected":s.get("duplicate_detected") is True,
 "audit_pass":s.get("audit_status")=="PASS","gate_complete":c.get("paper_order_gate_complete") is True,
 "actual_orders_zero":c.get("actual_orders_submitted")==0}
 f=[k for k,z in checks.items() if not z];print(json.dumps({"stage_range":"V83.01-V83.20","status":"PASS" if not f else "FAIL","checks":checks,"failed_checks":f,"next_phase":c.get("next_phase")},indent=2,sort_keys=True));return 0 if not f else 1
if __name__=="__main__":raise SystemExit(main())
