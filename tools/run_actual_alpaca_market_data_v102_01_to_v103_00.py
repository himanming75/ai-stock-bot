from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from market_data_engine import SubscriptionRegistry

CONFIRMATION = "CONNECT TO ALPACA PAPER MARKET DATA STREAM"


def main() -> int:
    parser = argparse.ArgumentParser(description="Optional Alpaca websocket market-data runner.")
    parser.add_argument("--symbols", nargs="+", default=["AAPL"])
    parser.add_argument("--confirm", required=True)
    args = parser.parse_args()

    if args.confirm != CONFIRMATION:
        raise SystemExit("CONFIRMATION TEXT MISMATCH - NO NETWORK CONNECTION")

    if os.environ.get("AI_STOCK_BOT_ENABLE_ACTUAL_MARKET_DATA") != "1":
        raise SystemExit("AI_STOCK_BOT_ENABLE_ACTUAL_MARKET_DATA=1 is required")

    key = os.environ.get("APCA_API_KEY_ID")
    secret = os.environ.get("APCA_API_SECRET_KEY")
    if not key or not secret:
        raise SystemExit("Alpaca credentials are required")

    try:
        import websocket
    except ImportError as exc:
        raise SystemExit(
            "Optional dependency missing. Install with: pip install websocket-client"
        ) from exc

    registry = SubscriptionRegistry()
    registry.subscribe(quotes=args.symbols, trades=args.symbols, bars=args.symbols)

    url = "wss://stream.data.alpaca.markets/v2/iex"
    auth = {"action":"auth","key":key,"secret":secret}
    subscribe = registry.alpaca_subscribe_message()

    def on_open(ws):
        ws.send(json.dumps(auth))
        ws.send(json.dumps(subscribe))

    def on_message(ws, message):
        print(message)

    def on_error(ws, error):
        print(f"ERROR: {error}", file=sys.stderr)

    app = websocket.WebSocketApp(url, on_open=on_open, on_message=on_message, on_error=on_error)
    app.run_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
