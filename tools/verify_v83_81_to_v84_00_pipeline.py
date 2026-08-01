from pathlib import Path
import argparse,hashlib,json
def h(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");a=p.parse_args();o=Path(a.repository_root).resolve()/"release/v84_00/output"
 cp=o/"paper_broker_final_certificate_v84_00.json";vp=o/"paper_broker_final_verify_v84_00.json";mp=o/"paper_broker_final_manifest_v83_93.json"
 for x in (cp,vp,mp):
  if not x.is_file():raise SystemExit(f"VERIFY FAIL: missing {x}")
 c=json.loads(cp.read_text());v=json.loads(vp.read_text());m=json.loads(mp.read_text());u=dict(c);e=u.pop("certificate_sha256",None);s=c.get("paper_broker_final_summary",{})
 checks={"certificate_status_pass":c.get("status")=="PASS","certificate_hash_valid":e==h(u),"verify_flag_true":v.get("verified") is True,
 "manifest_stage_v83_93":m.get("stage")=="V83.93","certificate_count_five":s.get("certificate_count")==5,
 "chain_pass":s.get("chain_status")=="PASS","order_fill_pass":s.get("order_fill_consistency_status")=="PASS",
 "ledger_pass":s.get("ledger_consistency_status")=="PASS","safety_pass":s.get("safety_audit_status")=="PASS",
 "replay_pass":s.get("replay_certification_status")=="PASS","compliance_pass":s.get("compliance_status")=="PASS",
 "readiness_pass":s.get("release_readiness_status")=="PASS","audit_pass":s.get("final_audit_status")=="PASS",
 "archive_pass":s.get("archive_status")=="PASS","framework_certified":c.get("paper_framework_certified") is True,
 "framework_complete":c.get("paper_broker_framework_complete") is True,"actual_orders_zero":c.get("actual_orders_submitted")==0}
 f=[k for k,z in checks.items() if not z];print(json.dumps({"stage_range":"V83.81-V84.00","status":"PASS" if not f else "FAIL","checks":checks,"failed_checks":f,"next_phase":c.get("next_phase")},indent=2,sort_keys=True));return 0 if not f else 1
if __name__=="__main__":raise SystemExit(main())
