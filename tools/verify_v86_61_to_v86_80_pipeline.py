from pathlib import Path
import argparse,json,hashlib
def h(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");a=p.parse_args()
 o=Path(a.repository_root).resolve()/"release/v86_80/output"
 c=json.loads((o/"final_network_certificate_v86_80.json").read_text())
 v=json.loads((o/"final_network_verify_v86_80.json").read_text())
 u=dict(c);e=u.pop("certificate_sha256");s=c["final_network_summary"]
 checks={"certificate_hash_valid":e==h(u),"status_pass":c["status"]=="PASS",
 "verify_flag_true":v["verified"] is True,"source_count_three":s["source_certificate_count"]==3,
 "safety_pass":s["safety_status"]=="PASS","compliance_pass":s["compliance_status"]=="PASS",
 "replay_pass":s["replay_status"]=="PASS","readiness_pass":s["readiness_status"]=="PASS",
 "audit_pass":s["audit_status"]=="PASS","framework_complete":c["paper_broker_network_framework_complete"] is True,
 "framework_certified":c["paper_broker_network_certified"] is True,
 "network_zero":c["network_requests_executed"]==0,"orders_zero":c["actual_orders_submitted"]==0}
 f=[k for k,v in checks.items() if not v]
 print(json.dumps({"stage_range":"V86.61-V86.80","status":"PASS" if not f else "FAIL",
 "checks":checks,"failed_checks":f,"evidence_classification":s["evidence_classification"],
 "release_candidate":s["release_candidate"],"next_phase":c["next_phase"]},indent=2,sort_keys=True))
 return 0 if not f else 1
if __name__=="__main__":raise SystemExit(main())
