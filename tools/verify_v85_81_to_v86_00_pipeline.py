from pathlib import Path
import argparse,hashlib,json
def h(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");a=p.parse_args();o=Path(a.repository_root).resolve()/"release/v86_00/output"
 cp=o/"paper_network_enablement_certificate_v86_00.json";vp=o/"paper_network_enablement_verify_v86_00.json";mp=o/"paper_network_enablement_manifest_v85_99.json"
 for x in (cp,vp,mp):
  if not x.is_file():raise SystemExit(f"VERIFY FAIL: missing {x}")
 c=json.loads(cp.read_text());v=json.loads(vp.read_text());m=json.loads(mp.read_text());u=dict(c);e=u.pop("certificate_sha256",None);s=c.get("paper_network_enablement_summary",{})
 checks={"certificate_status_pass":c.get("status")=="PASS","certificate_hash_valid":e==h(u),
 "verify_flag_true":v.get("verified") is True,"manifest_stage_v85_99":m.get("stage")=="V85.99",
 "approval_count_valid":s.get("approval_count",0)>=s.get("required_approvals",999),
 "receipt_ready":s.get("enablement_receipt_status")=="ENABLEMENT_FOUNDATION_READY",
 "revocation_supported":s.get("revocation_supported") is True,"risk_rejects_positive":s.get("risk_reject_count",0)>0,
 "read_capabilities_positive":s.get("read_capability_count",0)>0,"write_capabilities_zero":s.get("write_capability_count")==0,
 "one_order_limit_one":s.get("one_order_limit")==1,"rollback_pass":s.get("rollback_status")=="PASS",
 "audit_pass":s.get("audit_status")=="PASS",
 "foundation_complete":c.get("paper_network_enablement_foundation_complete") is True,
 "network_false":c.get("paper_network_enabled") is False,"orders_zero":c.get("actual_orders_submitted")==0}
 f=[k for k,z in checks.items() if not z];print(json.dumps({"stage_range":"V85.81-V86.00","status":"PASS" if not f else "FAIL","checks":checks,"failed_checks":f,"next_phase":c.get("next_phase")},indent=2,sort_keys=True));return 0 if not f else 1
if __name__=="__main__":raise SystemExit(main())
