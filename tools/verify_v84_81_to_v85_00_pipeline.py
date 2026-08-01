from pathlib import Path
import argparse,hashlib,json
def h(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");a=p.parse_args();o=Path(a.repository_root).resolve()/"release/v85_00/output"
 cp=o/"live_broker_final_certificate_v85_00.json";vp=o/"live_broker_final_verify_v85_00.json";mp=o/"live_broker_final_manifest_v84_93.json"
 for x in (cp,vp,mp):
  if not x.is_file():raise SystemExit(f"VERIFY FAIL: missing {x}")
 c=json.loads(cp.read_text());v=json.loads(vp.read_text());m=json.loads(mp.read_text());u=dict(c);e=u.pop("certificate_sha256",None);s=c.get("live_broker_final_summary",{})
 checks={"certificate_status_pass":c.get("status")=="PASS","certificate_hash_valid":e==h(u),"verify_flag_true":v.get("verified") is True,
 "manifest_stage_v84_93":m.get("stage")=="V84.93","certificate_count_four":s.get("certificate_count")==4,
 "chain_pass":s.get("chain_status")=="PASS","safety_pass":s.get("safety_status")=="PASS",
 "replay_pass":s.get("replay_status")=="PASS","authorization_pass":s.get("authorization_status")=="PASS",
 "gate_pass":s.get("gate_status")=="PASS","compliance_pass":s.get("compliance_status")=="PASS",
 "readiness_pass":s.get("release_readiness_status")=="PASS","audit_pass":s.get("final_audit_status")=="PASS",
 "archive_pass":s.get("archive_status")=="PASS","framework_certified":c.get("live_framework_certified") is True,
 "framework_complete":c.get("live_broker_framework_complete") is True,"actual_orders_zero":c.get("actual_orders_submitted")==0}
 f=[k for k,z in checks.items() if not z];print(json.dumps({"stage_range":"V84.81-V85.00","status":"PASS" if not f else "FAIL","checks":checks,"failed_checks":f,"next_phase":c.get("next_phase")},indent=2,sort_keys=True));return 0 if not f else 1
if __name__=="__main__":raise SystemExit(main())
