from pathlib import Path
import argparse,hashlib,json
def h(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");a=p.parse_args();o=Path(a.repository_root).resolve()/"release/v82_80/output"
 cp=o/"dry_run_broker_validation_certificate_v82_80.json";vp=o/"dry_run_broker_validation_verify_v82_80.json";mp=o/"dry_run_broker_manifest_v82_77.json"
 for x in (cp,vp,mp):
  if not x.is_file():raise SystemExit(f"VERIFY FAIL: missing {x}")
 c=json.loads(cp.read_text());v=json.loads(vp.read_text());m=json.loads(mp.read_text());u=dict(c);e=u.pop("certificate_sha256",None);s=c.get("dry_run_summary",{})
 checks={"certificate_status_pass":c.get("status")=="PASS","certificate_hash_valid":e==h(u),"verify_flag_true":v.get("verified") is True,
 "manifest_stage_v82_77":m.get("stage")=="V82.77","scenario_count_four":s.get("scenario_count")==4,
 "accepted_positive":s.get("accepted_count",0)>0,"rejected_positive":s.get("rejected_count",0)>0,
 "duplicate_detected":s.get("duplicate_detected") is True,"replay_deterministic":s.get("replay_deterministic") is True,
 "audit_pass":s.get("audit_status")=="PASS","validation_complete":c.get("dry_run_broker_validation_complete") is True,
 "actual_orders_zero":c.get("actual_orders_submitted")==0,"paper_not_authorized":c.get("paper_trading_authorized") is False,
 "live_not_authorized":c.get("live_trading_authorized") is False}
 f=[k for k,z in checks.items() if not z];print(json.dumps({"stage_range":"V82.61-V82.80","status":"PASS" if not f else "FAIL","checks":checks,"failed_checks":f,"next_phase":c.get("next_phase")},indent=2,sort_keys=True));return 0 if not f else 1
if __name__=="__main__":raise SystemExit(main())
