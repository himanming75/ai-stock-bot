
from pathlib import Path
import argparse

TARGET=Path("dashboard/operations_dashboard_v3_2.py")

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\stock-bot")
    a=p.parse_args()
    target=Path(a.root)/TARGET
    text=target.read_text(encoding="utf-8")

    if 'payload["broker_integration_v1"]' in text:
        print("BROKER INTEGRATION V1 SERVER ALREADY PRESENT")
        return 0

    marker = '''    return payload


class Handler(BaseHTTPRequestHandler):
'''

    replacement = '''    try:
        import sys
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))
        from broker_integration_v1.integrated_status import (
            build_broker_integration_v1_status,
        )
        payload["broker_integration_v1"] = (
            build_broker_integration_v1_status()
        )
        payload["broker_integration_v1_status"] = (
            payload["broker_integration_v1"].get("status", "PASS")
        )
    except Exception as exc:
        payload["broker_integration_v1"] = {
            "status": "ISOLATED_ERROR",
            "development_status": "ERROR",
            "network_status": "LOCKED",
            "live_trading_status": "LOCKED",
            "contracts": {
                "duplicate_broker_contract_created": False,
                "duplicate_alpaca_market_data_stack_created": False,
                "broker_network_used": False,
                "broker_write_performed": False,
                "order_submission_performed": False,
                "live_trading_enabled": False,
            },
        }
        payload["broker_integration_v1_status"] = (
            "ISOLATED_BROKER_INTEGRATION_ERROR: "
            + type(exc).__name__
        )

    return payload


class Handler(BaseHTTPRequestHandler):
'''

    if marker not in text:
        raise RuntimeError("BROKER V1 SERVER INSERT MARKER NOT FOUND")

    target.write_text(text.replace(marker,replacement,1),encoding="utf-8")
    print("BROKER INTEGRATION V1 SERVER: PASS")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
