from pathlib import Path
import argparse,hashlib,json
def h(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");a=p.parse_args();o=Path(a.repository_root).resolve()/"release/v85_40/output"
 cp=o/"paper_read_only_certificate_v85_40.json";vp=o/"paper_read_only_verify_v85_40.json";mp=o/"paper_read_only_manifest_v85_36.json"
 for x in (cp,vp,mp):
  if not x.is_file():raise SystemExit(f"VERIFY FAIL: missing {x}")
 c=json.loads(cp.read_text());v=json.loads(vp.read_text());m=json.loads(mp.read_text());u=dict(c);e=u.pop("certificate_sha256",None);s=c.get("paper_read_only_summary",{})
 checks={"certificate_status_pass":c.get("status")=="PASS","certificate_hash_valid":e==h(u),"verify_flag_true":v.get("verified") is True,
 "manifest_stage_v85_36":m.get("stage")=="V85.36","endpoint_count_six":s.get("endpoint_count")==6,
 "requests_all_success":s.get("request_success_count")==6,"schemas_all_pass":s.get("schema_pass_count")==6,
 "health_pass":s.get("health_status")=="PASS","reconciliation_pass":s.get("reconciliation_status")=="PASS",
 "audit_pass":s.get("audit_status")=="PASS","validation_complete":c.get("paper_read_only_validation_complete") is True,
 "orders_zero":c.get("actual_orders_submitted")==0,"paper_submit_false":c.get("paper_order_submission_authorized") is False}
 f=[k for k,z in checks.items() if not z];print(json.dumps({"stage_range":"V85.21-V85.40","status":"PASS" if not f else "FAIL","checks":checks,"failed_checks":f,"network_mode":s.get("network_mode"),"next_phase":c.get("next_phase")},indent=2,sort_keys=True));return 0 if not f else 1
if __name__=="__main__":raise SystemExit(main())
