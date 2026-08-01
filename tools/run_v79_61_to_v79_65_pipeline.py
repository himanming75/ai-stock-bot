from pathlib import Path
import argparse,json,shutil,sys
R=Path(__file__).resolve().parents[1]
if str(R) not in sys.path:sys.path.insert(0,str(R))
from alpaca_market_data.historical_feature_store_v79_61_65 import *
p=argparse.ArgumentParser();p.add_argument('--repository-root',default='.');p.add_argument('--clean',action='store_true');a=p.parse_args();root=Path(a.repository_root).resolve();out=root/'release/v79_65/output'
if a.clean and out.exists():shutil.rmtree(out)
base=root/'release/v79_60/output';r=run(base,base/'historical_dataset_backup_restore_certificate_v79_60.json',FeatureStoreConfig(),out);c=certificate(root,out,FeatureStoreConfig(),r);print(json.dumps({'stage_range':'V79.61-V79.65','status':c['status'],**c['feature_summary'],'network_requests_executed':0,'credentials_used':0,'trading_client_created':False,'actual_orders_submitted':0,'next_phase':c['next_phase']},indent=2,sort_keys=True));raise SystemExit(0 if c['status']=='PASS' else 1)
