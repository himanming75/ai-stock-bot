from pathlib import Path
import argparse,hashlib,json
def h(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");a=p.parse_args();o=Path(a.repository_root).resolve()/"release/v84_40/output"
 cp=o/"live_order_gate_certificate_v84_40.json";vp=o/"live_order_gate_verify_v84_40.json";mp=o/"live_order_gate_manifest_v84_40.json"
 for x in (cp,vp,mp):
  if not x.is_file():raise SystemExit(f"VERIFY FAIL: missing {x}")
 c=json.loads(cp.read_text());v=json.loads(vp.read_text());m=json.loads(mp.read_text());u=dict(c);e=u.pop("certificate_sha256",None);s=c.get("live_order_gate_summary",{})
 checks={"certificate_status_pass":c.get("status")=="PASS","certificate_hash_valid":e==h(u),"verify_flag_true":v.get("verified") is True,
 "manifest_stage_v84_40":m.get("stage")=="V84.40","scenario_count_four":s.get("scenario_count")==4,
 "gate_pass_positive":s.get("gate_pass_count",0)>0,"gate_reject_positive":s.get("gate_reject_count",0)>0,
 "duplicate_detected":s.get("duplicate_detected") is True,"replay_detected":s.get("replay_detected") is True,
 "audit_pass":s.get("audit_status")=="PASS","gate_complete":c.get("live_order_gate_complete") is True,
 "live_not_authorized":c.get("live_trading_authorized") is False,"actual_orders_zero":c.get("actual_orders_submitted")==0}
 f=[k for k,z in checks.items() if not z];print(json.dumps({"stage_range":"V84.21-V84.40","status":"PASS" if not f else "FAIL","checks":checks,"failed_checks":f,"next_phase":c.get("next_phase")},indent=2,sort_keys=True));return 0 if not f else 1
if __name__=="__main__":raise SystemExit(main())
