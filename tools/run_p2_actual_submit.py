from __future__ import annotations
import argparse
from decimal import Decimal
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alpaca_paper_read.adapter import AlpacaPaperReadAdapter
from alpaca_paper_read.http_client import ReadOnlyHttpClient
from alpaca_paper_read.config import ReadConfig
from broker_integration.client_order_id import generate_client_order_id
from broker_integration.execution_config import load_execution_config
from broker_integration.execution_http import AlpacaPaperExecutionHttp
from broker_integration.execution_models import CanonicalOrderRequest
from broker_integration.execution_service import submit_paper_order
from broker_integration.io import write_json
from broker_integration.market_data_http import AlpacaMarketDataReadHttp
from broker_integration.paths import BrokerStatePaths


parser = argparse.ArgumentParser()
parser.add_argument("--symbol", required=True)
parser.add_argument("--side", choices=["buy", "sell"], required=True)
parser.add_argument("--type", choices=["market", "limit"], required=True)
parser.add_argument("--tif", choices=["day", "gtc"], default="day")
size = parser.add_mutually_exclusive_group(required=True)
size.add_argument("--qty")
size.add_argument("--notional")
parser.add_argument("--limit-price")
parser.add_argument("--strategy-id", default="manual-p2-validation")
parser.add_argument("--client-order-id")
args = parser.parse_args()

config = load_execution_config()
client_order_id = args.client_order_id or generate_client_order_id(
    args.symbol,
    args.side,
    args.strategy_id,
)
order = CanonicalOrderRequest(
    symbol=args.symbol,
    side=args.side,
    order_type=args.type,
    time_in_force=args.tif,
    qty=Decimal(args.qty) if args.qty else None,
    notional=Decimal(args.notional) if args.notional else None,
    limit_price=(
        Decimal(args.limit_price)
        if args.limit_price
        else None
    ),
    client_order_id=client_order_id,
)

read_config = ReadConfig(
    api_key=config.api_key,
    secret_key=config.secret_key,
    base_url=config.base_url,
    timeout_seconds=config.timeout_seconds,
    maximum_attempts=config.maximum_attempts,
    backoff_seconds=config.backoff_seconds,
    actual_network_enabled=config.network_enabled,
)
read_adapter = AlpacaPaperReadAdapter(ReadOnlyHttpClient(read_config))
account = read_adapter.get_account()
clock = read_adapter.get_clock()
asset = read_adapter.get_asset(args.symbol)
positions = read_adapter.get_positions()

latest_trade_price = None
if order.order_type == "market" and order.qty is not None:
    latest_trade_price = Decimal(
        AlpacaMarketDataReadHttp(config).latest_trade_price(args.symbol)
    )

paths = BrokerStatePaths(ROOT)
kill_switch = json.loads(
    paths.kill_switch.read_text(encoding="utf-8-sig")
)

result = submit_paper_order(
    config=config,
    order=order,
    account=account,
    asset=asset,
    clock=clock,
    kill_switch=kill_switch,
    risk_permission=True,
    latest_trade_price=latest_trade_price,
    positions=positions,
    registry_path=paths.order_registry,
    order_ledger_path=paths.order_ledger,
    error_ledger_path=(
        paths.canonical_root / "order_error_ledger.jsonl"
    ),
    http=AlpacaPaperExecutionHttp(config),
)
write_json(
    paths.canonical_root / "latest_p2_execution_result.json",
    result,
)
print(json.dumps(result, indent=2, sort_keys=True))
raise SystemExit(0 if result["status"] == "PASS" else 1)
