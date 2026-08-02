from pathlib import Path
import argparse,json,os,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from alpaca_broker import AlpacaPaperClient,AlpacaPaperConfig,CredentialLoader,UrllibHttpTransport
from autonomous_paper_runtime.order_lifecycle import ExistingPaperOrderLifecycleTracker

ENABLE="AI_STOCK_BOT_ENABLE_ACTUAL_ORDER_LIFECYCLE_READ"
CONFIRM="AI_STOCK_BOT_ACTUAL_ORDER_LIFECYCLE_CONFIRMATION"
TEXT="READ ACTUAL ALPACA PAPER ORDER LIFECYCLE GET ONLY"

def main():
    p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");p.add_argument("--client-order-id",default="single-60d3c5406e5226ae71d7");a=p.parse_args()
    env=dict(os.environ)
    if env.get(ENABLE,"").upper()!="YES": raise SystemExit(f"{ENABLE}=YES is required")
    if env.get(CONFIRM,"")!=TEXT: raise SystemExit(f"{CONFIRM} must equal: {TEXT}")
    key,secret=CredentialLoader().load(env)
    client=AlpacaPaperClient(config=AlpacaPaperConfig(network_read_enabled=True,network_write_enabled=False,max_retries=2),api_key=key,secret_key=secret,transport=UrllibHttpTransport())
    order=client.get_order_by_client_id(a.client_order_id)
    r=ExistingPaperOrderLifecycleTracker().track(order,network_requests_executed=client.network_requests_executed)
    out={"stage_range":"V127.01-V128.00","status":"PASS","implementation_type":"EXISTING_PAPER_ORDER_LIFECYCLE_TRACKING","validation_mode":"ACTUAL_ALPACA_PAPER_GET_ONLY","actual_credentials_used":True,"actual_external_network_used":True,**r.to_json_dict(),"next_phase":"V128_01_FILL_AND_PORTFOLIO_RECONCILIATION" if r.terminal else "V128_01_CONTINUE_EXISTING_ORDER_LIFECYCLE_TRACKING"}
    path=Path(a.repository_root).resolve()/"release/v128_00/actual/actual_existing_paper_order_lifecycle_result.json";path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps(out,indent=2,sort_keys=True));print(f"RESULT_FILE={path}");return 0
if __name__=="__main__": raise SystemExit(main())
