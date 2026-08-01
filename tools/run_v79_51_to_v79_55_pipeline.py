from pathlib import Path
import argparse,json,shutil,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from alpaca_market_data import RecoveryConfig,run_dataset_recovery,build_recovery_certificate
def main():
 p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");p.add_argument("--clean",action="store_true");a=p.parse_args();r=Path(a.repository_root).resolve();o=r/"release/v79_55/output"
 if a.clean and o.exists():shutil.rmtree(o)
 v=r/"release/v79_45/output";t=r/"release/v79_50/output";c=RecoveryConfig();x=run_dataset_recovery(v/"dataset_version_registry.json",v/"versions",t/"archive",t/"historical_dataset_retention_certificate_v79_50.json",c,o);cert=build_recovery_certificate(r,o,c,x)
 print(json.dumps({"stage_range":"V79.51-V79.55","status":cert["status"],"passed_stage_count":cert["passed_stage_count"],"failed_stage_count":cert["failed_stage_count"],**cert["recovery_summary"],"network_requests_executed":0,"credentials_used":0,"trading_client_created":False,"actual_orders_submitted":0,"next_phase":cert["next_phase"]},indent=2,sort_keys=True));return 0 if cert["status"]=="PASS" else 1
if __name__=="__main__":raise SystemExit(main())
