from pathlib import Path
import argparse,hashlib,json
def h(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");a=p.parse_args();o=Path(a.repository_root).resolve()/"release/v83_80/output"
 cp=o/"paper_broker_execution_sim_certificate_v83_80.json";vp=o/"paper_broker_execution_sim_verify_v83_80.json";mp=o/"paper_broker_execution_manifest_v83_74.json"
 for x in (cp,vp,mp):
  if not x.is_file():raise SystemExit(f"VERIFY FAIL: missing {x}")
 c=json.loads(cp.read_text());v=json.loads(vp.read_text());m=json.loads(mp.read_text());u=dict(c);e=u.pop("certificate_sha256",None);s=c.get("paper_broker_execution_summary",{})
 checks={"certificate_status_pass":c.get("status")=="PASS","certificate_hash_valid":e==h(u),"verify_flag_true":v.get("verified") is True,
 "manifest_stage_v83_74":m.get("stage")=="V83.74","order_count_five":s.get("order_count")==5,
 "fills_positive":s.get("fill_count",0)>0,"filled_positive":s.get("filled_order_count",0)>0,
 "partial_positive":s.get("partial_order_count",0)>0,"canceled_positive":s.get("canceled_order_count",0)>0,
 "rejected_positive":s.get("rejected_order_count",0)>0,"closing_cash_positive":s.get("closing_cash",0)>0,
 "replay_deterministic":s.get("replay_deterministic") is True,"audit_pass":s.get("audit_status")=="PASS",
 "simulation_complete":c.get("paper_broker_execution_simulation_complete") is True,"actual_orders_zero":c.get("actual_orders_submitted")==0}
 f=[k for k,z in checks.items() if not z];print(json.dumps({"stage_range":"V83.61-V83.80","status":"PASS" if not f else "FAIL","checks":checks,"failed_checks":f,"next_phase":c.get("next_phase")},indent=2,sort_keys=True));return 0 if not f else 1
if __name__=="__main__":raise SystemExit(main())
