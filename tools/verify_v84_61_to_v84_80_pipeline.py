from pathlib import Path
import argparse,hashlib,json
def h(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");a=p.parse_args();o=Path(a.repository_root).resolve()/"release/v84_80/output"
 cp=o/"live_order_submission_sim_certificate_v84_80.json";vp=o/"live_order_submission_sim_verify_v84_80.json";mp=o/"live_order_submission_sim_manifest_v84_78.json"
 for x in (cp,vp,mp):
  if not x.is_file(): raise SystemExit(f"VERIFY FAIL: missing {x}")
 c=json.loads(cp.read_text());v=json.loads(vp.read_text());m=json.loads(mp.read_text());u=dict(c);e=u.pop("certificate_sha256",None);s=c.get("live_order_submission_summary",{})
 checks={"certificate_status_pass":c.get("status")=="PASS","certificate_hash_valid":e==h(u),"verify_flag_true":v.get("verified") is True,
 "manifest_stage_v84_78":m.get("stage")=="V84.78","scenario_count_four":s.get("scenario_count")==4,
 "ack_count_four":s.get("ack_count")==4,"accepted_positive":s.get("accepted_count",0)>0,
 "rejected_positive":s.get("rejected_count",0)>0,"partial_positive":s.get("partial_count",0)>0,
 "authorization_reject_positive":s.get("authorization_reject_count",0)>0,
 "duplicate_detected":s.get("duplicate_detected") is True,"replay_detected":s.get("replay_detected") is True,
 "deterministic_replay":s.get("deterministic_replay") is True,"audit_pass":s.get("audit_status")=="PASS",
 "simulation_complete":c.get("live_order_submission_simulation_complete") is True,
 "live_not_authorized":c.get("live_trading_authorized") is False,"actual_orders_zero":c.get("actual_orders_submitted")==0}
 f=[k for k,z in checks.items() if not z];print(json.dumps({"stage_range":"V84.61-V84.80","status":"PASS" if not f else "FAIL","checks":checks,"failed_checks":f,"next_phase":c.get("next_phase")},indent=2,sort_keys=True));return 0 if not f else 1
if __name__=="__main__":raise SystemExit(main())
