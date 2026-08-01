from pathlib import Path
import argparse,json,hashlib
def h(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");a=p.parse_args()
 o=Path(a.repository_root).resolve()/"release/v87_40/output"
 c=json.loads((o/"strategy_execution_sim_certificate_v87_40.json").read_text())
 v=json.loads((o/"strategy_execution_sim_verify_v87_40.json").read_text())
 u=dict(c);e=u.pop("certificate_sha256");s=c["strategy_execution_simulation_summary"]
 checks={"certificate_hash_valid":e==h(u),"status_pass":c["status"]=="PASS",
 "verify_flag_true":v["verified"] is True,
 "accepted_count_one":s["accepted_count"]==1,
 "partial_count_one":s["partial_count"]==1,
 "filled_count_one":s["filled_count"]==1,
 "rejected_count_one":s["rejected_count"]==1,
 "canceled_count_one":s["canceled_count"]==1,
 "closing_cash_positive":s["closing_cash"]>0,
 "position_positive":s["position_qty"]>0,
 "retry_initial_allowed":s["retry_initial_allowed"],
 "retry_exhausted_blocked":s["retry_exhausted_blocked"],
 "replay_deterministic":s["replay_deterministic"],
 "rollback_pass":s["rollback_status"]=="PASS",
 "audit_pass":s["audit_status"]=="PASS",
 "simulation_complete":c["paper_strategy_execution_simulation_complete"] is True,
 "engine_simulated":c["strategy_execution_engine_simulated"] is True,
 "network_zero":c["network_requests_executed"]==0,
 "orders_zero":c["actual_orders_submitted"]==0}
 f=[k for k,v in checks.items() if not v]
 print(json.dumps({"stage_range":"V87.21-V87.40","status":"PASS" if not f else "FAIL",
 "checks":checks,"failed_checks":f,"next_phase":c["next_phase"]},indent=2,sort_keys=True))
 return 0 if not f else 1
if __name__=="__main__":raise SystemExit(main())
