from pathlib import Path
import argparse,hashlib,json
def h(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");a=p.parse_args();o=Path(a.repository_root).resolve()/"release/v86_20/output"
 cp=o/"single_order_certificate_v86_20.json";vp=o/"single_order_verify_v86_20.json";mp=o/"single_order_manifest_v86_15.json"
 for x in (cp,vp,mp):
  if not x.is_file():raise SystemExit("VERIFY FAIL: missing "+str(x))
 c=json.loads(cp.read_text());v=json.loads(vp.read_text());u=dict(c);e=u.pop("certificate_sha256",None);s=c["single_order_summary"]
 checks={"certificate_status_pass":c["status"]=="PASS","certificate_hash_valid":e==h(u),"verify_flag_true":v["verified"] is True,
 "preflight_pass":s["preflight_status"]=="PASS","token_issued":s["token_issued"],"read_after_write_pass":s["read_after_write_status"]=="PASS",
 "token_revoked":s["token_revoked"],"rollback_pass":s["rollback_status"]=="PASS","audit_pass":s["audit_status"]=="PASS",
 "one_order_or_less":s["actual_orders_submitted"]<=1,"validation_complete":c["paper_single_order_validation_complete"] is True}
 f=[k for k,z in checks.items() if not z];print(json.dumps({"stage_range":"V86.01-V86.20","status":"PASS" if not f else "FAIL","checks":checks,"failed_checks":f,"network_mode":s["network_mode"],"next_phase":c["next_phase"]},indent=2,sort_keys=True));return 0 if not f else 1
if __name__=="__main__":raise SystemExit(main())
