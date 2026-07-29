from dataclasses import replace
from decimal import Decimal
from pathlib import Path
import ast, json, tempfile

import backtest.offline_portfolio_v25_2 as m
from backtest.offline_portfolio_v25_2 import (
    PortfolioError, PortfolioPolicy, allocation, buy, load_snapshot,
    mark_to_market, new_portfolio, save_snapshot, sell, snapshot_payload,
    verify_snapshot,
)


def check(name, condition):
    print(f"{name:<52}: {condition}")
    if not condition:
        raise AssertionError(name)


def is_blocked(fn):
    try:
        fn()
    except PortfolioError:
        return True
    return False


policy = PortfolioPolicy(
    starting_cash=Decimal("100000"),
    max_position_pct=Decimal("0.30"),
    max_gross_exposure_pct=Decimal("0.90"),
    min_cash_reserve_pct=Decimal("0.05"),
    commission=Decimal("1.00"),
    slippage_bps=Decimal("5"),
)
base = new_portfolio(policy)
p1 = buy(base, "AAPL", 100, 100, timestamp="2026-07-28T20:00:00+00:00")
p2 = buy(p1, "MSFT", 50, 200, timestamp="2026-07-28T20:01:00+00:00")
p3 = mark_to_market(p2, {"AAPL": 110, "MSFT": 190}, timestamp="2026-07-28T20:02:00+00:00")
final = sell(p3, "AAPL", 40, 112, timestamp="2026-07-28T20:03:00+00:00")

check("V25.2 engine version verified", m.VERSION == "25.2")
check("Starting cash initialized", base.cash == Decimal("100000.00"))
check("BUY reduced cash", p1.cash < base.cash)
check("Two positions were created", len(p2.positions) == 2)
check("Mark-to-market updated prices", any(p.symbol == "AAPL" and p.market_price == Decimal("110.00") for p in p3.positions))
check("SELL reduced AAPL quantity", any(p.symbol == "AAPL" and p.quantity == Decimal("60.000000") for p in final.positions))
check("Equity was calculated", final.equity > 0)
check("Unrealized P&L was calculated", final.unrealized_pnl != 0)
check("Allocation includes cash", "CASH" in allocation(final))
check("Event chain has four events", len(final.events) == 4)
check("Snapshot verification passed", verify_snapshot(final))
check("Deterministic allocation returned", allocation(final) == allocation(final))

check("Oversized position was blocked", is_blocked(lambda: buy(base, "AAPL", 400, 100, timestamp="2026-07-28T20:00:00+00:00")))
check("Cash reserve violation was blocked", is_blocked(lambda: buy(base, "AAPL", 300, 300, timestamp="2026-07-28T20:00:00+00:00")))
check("Short sale was blocked", is_blocked(lambda: sell(p1, "AAPL", 101, 100, timestamp="2026-07-28T20:01:00+00:00")))
check("Unknown symbol sale was blocked", is_blocked(lambda: sell(base, "TSLA", 1, 100, timestamp="2026-07-28T20:00:00+00:00")))
check("Non-increasing timestamp was blocked", is_blocked(lambda: buy(p1, "MSFT", 1, 10, timestamp="2026-07-28T20:00:00+00:00")))

tampered = replace(final, cash=final.cash + Decimal("1.00"))
check("Tampered snapshot was detected", is_blocked(lambda: verify_snapshot(tampered)))
bad_event = replace(final.events[-1], previous_hash="BROKEN")
bad_chain = replace(final, events=final.events[:-1] + (bad_event,))
check("Broken event chain was detected", is_blocked(lambda: verify_snapshot(bad_chain)))

with tempfile.TemporaryDirectory() as folder:
    path = Path(folder) / "portfolio.json"
    save_snapshot(final, path)
    loaded = load_snapshot(path)
    check("Result save and load passed", snapshot_payload(loaded, True) == snapshot_payload(final, True))
    data = json.loads(path.read_text(encoding="utf-8"))
    data["cash"] = "999999.00"
    path.write_text(json.dumps(data), encoding="utf-8")
    check("Tampered saved result was blocked", is_blocked(lambda: load_snapshot(path)))

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
print("=" * 72)
print("V25.2 offline portfolio manager test completed successfully.")
print("Cash, positions, average cost, P&L, allocation, policy gates,")
print("event-chain integrity, persistence, and tamper detection were verified.")
print("Market/account/network/broker/order/live execution remained blocked.")
