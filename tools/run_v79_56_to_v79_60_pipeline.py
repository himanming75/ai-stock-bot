from pathlib import Path
import argparse,json,shutil,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from alpaca_market_data import BackupRestoreConfig,run_backup_restore,build_backup_restore_certificate

def main():
 p=argparse.ArgumentParser(); p.add_argument('--repository-root',default='.'); p.add_argument('--clean',action='store_true'); a=p.parse_args(); root=Path(a.repository_root).resolve(); out=root/'release/v79_60/output'
 if a.clean and out.exists(): shutil.rmtree(out)
 recovery=root/'release/v79_55/output'; config=BackupRestoreConfig(); result=run_backup_restore(recovery,recovery/'historical_dataset_recovery_certificate_v79_55.json',config,out); cert=build_backup_restore_certificate(root,out,config,result)
 print(json.dumps({'stage_range':'V79.56-V79.60','status':cert['status'],'passed_stage_count':cert['passed_stage_count'],'failed_stage_count':cert['failed_stage_count'],**cert['backup_restore_summary'],'network_requests_executed':cert['network_requests_executed'],'credentials_used':cert['credentials_used'],'trading_client_created':cert['trading_client_created'],'actual_orders_submitted':cert['actual_orders_submitted'],'next_phase':cert['next_phase']},indent=2,sort_keys=True)); return 0 if cert['status']=='PASS' else 1
if __name__=='__main__': raise SystemExit(main())
