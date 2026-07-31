from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alpaca_market_data import inspect_historical_installation

def main() -> int:
    status = inspect_historical_installation()
    result = status.to_dict()
    result.update({
        "stage_range": "V79.06-V79.10",
        "python": sys.version.split()[0],
        "network_test_performed": False,
        "credentials_used": False,
        "broker_connected": False,
        "trading_client_created": False,
        "actual_orders_submitted": 0,
    })
    required = (
        status.alpaca_py_installed
        and status.stock_historical_client_importable
        and status.stock_bars_request_importable
        and status.dataframe_support_available
    )
    result["status"] = "PASS" if required else "FAIL"
    print(json.dumps(result, indent=2, sort_keys=True))
    if not required:
        print('\nREQUIRED INSTALL COMMAND:')
        print('python -m pip install "alpaca-py>=0.43.5" pandas')
    return 0 if required else 1

if __name__ == "__main__":
    raise SystemExit(main())
