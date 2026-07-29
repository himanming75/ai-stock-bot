from dataclasses import replace
from decimal import Decimal
from pathlib import Path
import ast, json, tempfile

import backtest.offline_order_sim_v25_5 as m
from backtest.offline_order_sim_v25_5 import (
    Bar, ExecutionPolicy, OrderSimError, cancel_order, create_order,
    load_order, process_bar, save_order, verify_fill, verify_order,
)


def check(name, condition):
    print(f"{name:<58}: {condition}")
    if not condition:
        raise AssertionError(name)


def blocked(fn):
    try:
        fn()
    except OrderSimError:
        return True
    return False


policy = ExecutionPolicy(
    commission_per_order=Decimal("1.00"),
    slippage_bps=Decimal("10"),
    participation_rate=Decimal("0.50"),
)

bar = Bar("2026-07-28T20:00:00+00:00", 100, 105, 95, 102, 100)

market = create_order("O1", "AAPL", "BUY", "MARKET", 40)
market_after, market_fill = process_bar(market, bar, 0, policy)

limit = create_order("O2", "AAPL", "BUY", "LIMIT", 20, limit_price=98)
limit_after, limit_fill = process_bar(limit, bar, 0, policy)

stop = create_order("O3", "AAPL", "BUY", "STOP", 10, stop_price=103)
stop_after, stop_fill = process_bar(stop, bar, 0, policy)

stop_limit = create_order("O4", "AAPL", "SELL", "STOP_LIMIT", 10, stop_price=97, limit_price=96)
stop_limit_after, stop_limit_fill = process_bar(stop_limit, bar, 0, policy)

partial = create_order("O5", "MSFT", "BUY", "MARKET", 100)
partial_after, partial_fill = process_bar(
    partial,
    Bar("2026-07-28T20:01:00+00:00", 200, 202, 198, 201, 50),
    0,
    policy,
)

check("V25.5 engine version verified", m.VERSION == "25.5")
check("Market order filled", market_after.status == "FILLED")
check("Market fill created", market_fill is not None and verify_fill(market_fill))
check("Limit order filled", limit_after.status == "FILLED")
check("Stop order triggered and filled", stop_after.triggered and stop_after.status == "FILLED")
check("Stop-limit order triggered and filled", stop_limit_after.triggered and stop_limit_after.status == "FILLED")
check("Partial fill was created", partial_after.status == "PARTIALLY_FILLED")
check("Partial fill quantity respected participation", partial_after.filled_quantity == Decimal("25.000000"))
check("Commission charged once", partial_after.commission_paid == Decimal("1.00"))
check("Slippage applied to market buy", market_after.average_fill_price == Decimal("100.10"))
check("Order hash verified", verify_order(market_after))
check("Deterministic result returned", process_bar(market, bar, 0, policy)[0] == market_after)

second_after, second_fill = process_bar(
    partial_after,
    Bar("2026-07-28T20:02:00+00:00", 201, 203, 199, 202, 200),
    1,
    policy,
)
check("Second bar completed partial order", second_after.status == "FILLED")
check("Second fill created", second_fill is not None and verify_fill(second_fill))
check("Commission was not charged twice", second_after.commission_paid == Decimal("1.00"))

ioc = create_order("O6", "TSLA", "BUY", "LIMIT", 5, limit_price=80, tif="IOC")
ioc_after, ioc_fill = process_bar(ioc, bar, 0, policy)
check("IOC unfilled order cancelled", ioc_after.status == "CANCELLED" and ioc_fill is None)

day = create_order("O7", "NVDA", "BUY", "LIMIT", 5, limit_price=80, tif="DAY", expire_index=0)
day_after, _ = process_bar(day, bar, 0, policy)
check("DAY order expired", day_after.status == "EXPIRED")

gtc = create_order("O8", "AMD", "SELL", "LIMIT", 5, limit_price=150)
cancelled = cancel_order(gtc)
check("Manual cancellation passed", cancelled.status == "CANCELLED")

check("Invalid order type blocked", blocked(lambda: create_order("X", "AAPL", "BUY", "BAD", 1)))
check("Missing limit price blocked", blocked(lambda: create_order("X", "AAPL", "BUY", "LIMIT", 1)))
check("Missing stop price blocked", blocked(lambda: create_order("X", "AAPL", "BUY", "STOP", 1)))
check("Invalid bar blocked", blocked(lambda: process_bar(market, Bar("x", 100, 90, 95, 99, 10), 0, policy)))

tampered = replace(market_after, filled_quantity=Decimal("1"))
check("Tampered order detected", blocked(lambda: verify_order(tampered)))

with tempfile.TemporaryDirectory() as folder:
    path = Path(folder) / "order.json"
    save_order(market_after, path)
    loaded = load_order(path)
    check("Order save and load passed", loaded == market_after)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["status"] = "CANCELLED"
    path.write_text(json.dumps(payload), encoding="utf-8")
    check("Tampered saved order blocked", blocked(lambda: load_order(path)))

tree = ast.parse(Path(m.__file__).read_text(encoding="utf-8"))
forbidden = {"requests", "urllib", "httpx", "aiohttp", "socket", "alpaca_trade_api", "ib_insync", "ccxt"}
imports = set()
for node in ast.walk(tree):
    if isinstance(node, ast.Import):
        imports.update(alias.name.split(".")[0] for alias in node.names)
    elif isinstance(node, ast.ImportFrom) and node.module:
        imports.add(node.module.split(".")[0])

check("Forbidden network/broker imports are absent", not (imports & forbidden))
check("Market data API was not called", not m.MARKET_DATA_API_CALLED)
check("Account API was not called", not m.ACCOUNT_API_CALLED)
check("Network was not accessed", not m.NETWORK_ACCESSED)
check("Broker API was not called", not m.BROKER_API_CALLED)
check("Broker order was not created", not m.BROKER_ORDER_CREATED)
check("Order was not submitted", not m.ORDER_SUBMITTED)
check("Live execution not authorized", not m.LIVE_EXECUTION_AUTHORIZED)
check("Funds were not reserved", not m.FUNDS_RESERVED)
check("Holdings were not reserved", not m.HOLDINGS_RESERVED)
check("All checks passed", True)

print("=" * 78)
print("V25.5 offline order simulator test completed successfully.")
print("Market, limit, stop, stop-limit, partial fills, slippage, commission,")
print("time-in-force, cancellation, persistence, hashing, and tamper checks passed.")
print("Market/account/network/broker/order/live execution remained blocked.")
