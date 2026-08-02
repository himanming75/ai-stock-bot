from pathlib import Path
import argparse,json
def main():
 p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");a=p.parse_args()
 r=json.loads((Path(a.repository_root).resolve()/"release/v128_00/output/existing_paper_order_lifecycle_result.json").read_text())
 checks={"status_pass":r["status"]=="PASS","active":r["lifecycle_class"]=="ACTIVE","accepted":r["broker_status"]=="ACCEPTED","terminal_false":r["terminal"] is False,"new_order_blocked":r["new_order_allowed"] is False,"guard":r["active_order_guard_verified"] is True,"paper_zero":r["actual_paper_orders_submitted"]==0,"write_zero":r["write_requests_executed"]==0,"live_zero":r["live_orders_submitted"]==0}
 failed=[k for k,v in checks.items() if not v];out={"stage_range":"V127.01-V128.00","status":"PASS" if not failed else "FAIL","checks":checks,"failed_checks":failed,"next_phase":r["next_phase"]};print(json.dumps(out,indent=2,sort_keys=True));return 0 if not failed else 1
if __name__=="__main__": raise SystemExit(main())
