from pathlib import Path
import argparse,hashlib,json
def h(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");a=p.parse_args();o=Path(a.repository_root).resolve()/"release/v83_00/output"
 cp=o/"paper_broker_enablement_certificate_v83_00.json";vp=o/"paper_broker_enablement_verify_v83_00.json";mp=o/"paper_broker_enablement_manifest_v82_95.json"
 for x in (cp,vp,mp):
  if not x.is_file():raise SystemExit(f"VERIFY FAIL: missing {x}")
 c=json.loads(cp.read_text());v=json.loads(vp.read_text());m=json.loads(mp.read_text());u=dict(c);e=u.pop("certificate_sha256",None);s=c.get("paper_broker_summary",{})
 checks={"certificate_status_pass":c.get("status")=="PASS","certificate_hash_valid":e==h(u),"verify_flag_true":v.get("verified") is True,
 "manifest_stage_v82_95":m.get("stage")=="V82.95","approval_count_valid":s.get("approval_count",0)>=s.get("required_approvals",999),
 "receipt_issued":s.get("permission_receipt_status")=="ISSUED","scope_preview_only":s.get("permission_scope")=="PAPER_PREVIEW_AND_SESSION_ONLY",
 "paper_session_authorized":s.get("paper_session_authorized") is True,"paper_order_submit_false":s.get("paper_order_submission_authorized") is False,
 "live_not_authorized":s.get("live_trading_authorized") is False,"write_capabilities_zero":s.get("write_capability_count")==0,
 "health_pass":s.get("health_status")=="PASS","audit_pass":s.get("audit_status")=="PASS",
 "enablement_complete":c.get("paper_broker_enablement_complete") is True,"actual_orders_zero":c.get("actual_orders_submitted")==0}
 f=[k for k,z in checks.items() if not z];print(json.dumps({"stage_range":"V82.81-V83.00","status":"PASS" if not f else "FAIL","checks":checks,"failed_checks":f,"next_phase":c.get("next_phase")},indent=2,sort_keys=True));return 0 if not f else 1
if __name__=="__main__":raise SystemExit(main())
