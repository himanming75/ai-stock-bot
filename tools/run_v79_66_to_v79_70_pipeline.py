from pathlib import Path
import argparse,json,shutil,sys
R=Path(__file__).resolve().parents[1]
if str(R) not in sys.path:sys.path.insert(0,str(R))
from alpaca_market_data.historical_indicator_library_v79_66_70 import *
def main():
 p=argparse.ArgumentParser();p.add_argument('--repository-root',default='.');p.add_argument('--clean',action='store_true');a=p.parse_args();root=Path(a.repository_root).resolve();out=root/'release/v79_70/output'
 if a.clean and out.exists():shutil.rmtree(out)
 prior=root/'release/v79_65/output';c=IndicatorConfig();r=run_indicator_library(prior,prior/'historical_feature_store_certificate_v79_65.json',c,out);cert=build_indicator_certificate(root,out,c,r);print(json.dumps({'stage_range':'V79.66-V79.70','status':cert['status'],**cert['indicator_summary'],'network_requests_executed':0,'credentials_used':0,'trading_client_created':False,'actual_orders_submitted':0,'next_phase':cert['next_phase']},indent=2,sort_keys=True));return 0 if cert['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
