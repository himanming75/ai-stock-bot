import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
def main():
    checks={}
    try:
        from alpaca.data.historical import StockHistoricalDataClient
        checks["stock_historical_client_importable"]=True
    except Exception:
        checks["stock_historical_client_importable"]=False
    try:
        import pydantic
        checks["pydantic_importable"]=True
    except Exception:
        checks["pydantic_importable"]=False
    status="PASS" if all(checks.values()) else "FAIL"
    print(json.dumps({"stage_range":"V79.11-V79.15","status":status,**checks,
      "network_test_performed":False,"credentials_read":False,
      "trading_client_created":False,"actual_orders_submitted":0},indent=2,sort_keys=True))
    return 0 if status=="PASS" else 1
if __name__=="__main__": raise SystemExit(main())
