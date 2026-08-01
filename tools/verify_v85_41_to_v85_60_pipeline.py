from pathlib import Path
import argparse,hashlib,json
def h(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");a=p.parse_args();o=Path(a.repository_root).resolve()/"release/v85_60/output"
 cp=o/"paper_order_authorization_certificate_v85_60.json";vp=o/"paper_order_authorization_verify_v85_60.json";mp=o/"paper_order_authorization_manifest_v85_60.json"
 for x in (cp,vp,mp):
  if not x.is_file():raise SystemExit(f"VERIFY FAIL: missing {x}")
 c=json.loads(cp.read_text());v=json.loads(vp.read_text());m=json.loads(mp.read_text());u=dict(c);e=u.pop("certificate_sha256",None);s=c.get("paper_order_authorization_summary",{})
 checks={"certificate_status_pass":c.get("status")=="PASS","certificate_hash_valid":e==h(u),"verify_flag_true":v.get("verified") is True,
 "manifest_stage_v85_60":m.get("stage")=="V85.60","approval_count_valid":s.get("approval_count",0)>=s.get("required_approvals",999),
 "token_issued":s.get("token_issued") is True,"token_validation_pass":s.get("token_validation_status")=="PASS",
 "receipt_ready":s.get("receipt_status")=="AUTHORIZATION_READY","single_use_consumed":s.get("single_use_consumed") is True,
 "risk_rejects_positive":s.get("risk_reject_count",0)>0,"duplicate_detected":s.get("duplicate_detected") is True,
 "replay_detected":s.get("replay_detected") is True,"audit_pass":s.get("audit_status")=="PASS",
 "authorization_complete":c.get("paper_order_authorization_complete") is True,
 "paper_submit_false":c.get("paper_order_submission_authorized") is False,
 "orders_zero":c.get("actual_orders_submitted")==0}
 f=[k for k,z in checks.items() if not z];print(json.dumps({"stage_range":"V85.41-V85.60","status":"PASS" if not f else "FAIL","checks":checks,"failed_checks":f,"next_phase":c.get("next_phase")},indent=2,sort_keys=True));return 0 if not f else 1
if __name__=="__main__":raise SystemExit(main())
