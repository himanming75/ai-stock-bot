from pathlib import Path
import json, os, sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from alpaca_market_data import (
    NetworkSmokeConfig, inspect_network_smoke_preflight,
    execute_historical_network_smoke, sanitize_smoke_result,
)
def main():
    config=NetworkSmokeConfig()
    preflight=inspect_network_smoke_preflight(os.environ)
    result=execute_historical_network_smoke(os.environ,config)
    sanitized=sanitize_smoke_result(result)
    print(json.dumps({
      "preflight":preflight.to_dict(),
      "result":sanitized,
      "warning":"No credential values or raw market response are displayed."
    },indent=2,sort_keys=True))
    if result.status=="FAIL": return 1
    if result.status=="SKIPPED_SAFE":
        print("\nSet ALPACA_ENABLE_NETWORK_SMOKE=YES and Alpaca credential variables to execute one bounded request.")
    return 0
if __name__=="__main__": raise SystemExit(main())
