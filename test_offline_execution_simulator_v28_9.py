from dataclasses import replace
from decimal import Decimal
from pathlib import Path
import ast, json, tempfile

import backtest.offline_execution_simulator_v28_9 as m
from backtest.offline_execution_simulator_v28_9 import (
    ExecutionError,
    ExecutionPolicy,
    MarketBar,
    create_history,
    create_order,
    load_history,
    save_history,
    simulate_execution,
    verify_history,
    verify_order,
    verify_report,
)

def check(name, condition):
    print(f"{name:<96}: {condition}")
    if not condition:
        raise AssertionError(name)

def blocked(fn):
    try:
        fn()
    except ExecutionError:
        return True
    return False

policy = ExecutionPolicy(
    slippage_bps=Decimal("5"),
    commission_per_share=Decimal("0.005"),
    minimum_commission=Decimal("1.00"),
    max_participation_rate=Decimal("0.20"),
)

bars = (
    MarketBar("2026-07-29T13:30:00Z", Decimal("100"), Decimal("102"), Decimal("99"), Decimal("101"), 300),
    MarketBar("2026-07-29T13:31:00Z", Decimal("101"), Decimal("103"), Decimal("100"), Decimal("102"), 400),
)

market = create_order(
    order_id="O-MKT", timestamp="T", symbol="AAPL", side="BUY",
    order_type="MARKET", time_in_force="DAY", quantity=100,
    strategy_hash="a"*64,
)
limit = create_order(
    order_id="O-LMT", timestamp="T", symbol="MSFT", side="BUY",
    order_type="LIMIT", time_in_force="DAY", quantity=50,
    limit_price=Decimal("100"), strategy_hash="b"*64,
)
ioc = create_order(
    order_id="O-IOC", timestamp="T", symbol="NVDA", side="SELL",
    order_type="MARKET", time_in_force="IOC", quantity=100,
    strategy_hash="c"*64,
)
fok = create_order(
    order_id="O-FOK", timestamp="T", symbol="TSLA", side="BUY",
    order_type="MARKET", time_in_force="FOK", quantity=1000,
    strategy_hash="d"*64,
)
stop_limit = create_order(
    order_id="O-STP", timestamp="T", symbol="AMD", side="BUY",
    order_type="STOP_LIMIT", time_in_force="DAY", quantity=20,
    stop_price=Decimal("101"), limit_price=Decimal("102"), strategy_hash="e"*64,
)

market_report = simulate_execution(market, bars, policy)
limit_report = simulate_execution(limit, bars, policy)
ioc_report = simulate_execution(ioc, bars, policy)
fok_report = simulate_execution(fok, bars, policy)
stop_report = simulate_execution(stop_limit, bars, policy)

check("V28.9 engine version verified", m.VERSION == "28.9")
check("Market order created", verify_order(market))
check("Market order filled", market_report.status == "FILLED")
check("Limit order filled", limit_report.status == "FILLED")
check("Stop-limit order filled", stop_report.status == "FILLED")
check("IOC partial fill created", ioc_report.status == "PARTIALLY_FILLED")
check("IOC remainder cancelled", "IOC_REMAINDER_CANCELLED" in ioc_report.reason_codes)
check("FOK insufficient liquidity cancelled", fok_report.status == "CANCELLED")
check("FOK reason recorded", "FOK_NOT_FILLED" in fok_report.reason_codes)
check("Partial fills recorded", len(market_report.fills) == 2)
check("VWAP average fill price calculated", market_report.average_fill_price > Decimal("0"))
check("Slippage applied to BUY fill", market_report.fills[0].price > Decimal("100"))
check("Commission calculated", market_report.total_commission >= Decimal("1.00"))
check("Requested quantity tracked", market_report.requested_quantity == 100)
check("Filled quantity tracked", market_report.filled_quantity == 100)
check("Remaining quantity tracked", market_report.remaining_quantity == 0)
check("Execution report hash verified", verify_report(market_report))
check("Deterministic execution returned", market_report == simulate_execution(market, bars, policy))

no_fill_order = create_order(
    order_id="O-NONE", timestamp="T", symbol="META", side="BUY",
    order_type="LIMIT", time_in_force="DAY", quantity=10,
    limit_price=Decimal("90"), strategy_hash="f"*64,
)
no_fill = simulate_execution(no_fill_order, bars, policy)
check("Unfilled DAY order expired", no_fill.status == "EXPIRED")
check("No-fill reason recorded", "NO_ELIGIBLE_FILL" in no_fill.reason_codes)

check("Invalid order side blocked", blocked(lambda: create_order(
    order_id="BAD", timestamp="T", symbol="AAPL", side="SHORT",
    order_type="MARKET", time_in_force="DAY", quantity=1, strategy_hash="1"*64,
)))
check("Invalid order type blocked", blocked(lambda: create_order(
    order_id="BAD", timestamp="T", symbol="AAPL", side="BUY",
    order_type="BAD", time_in_force="DAY", quantity=1, strategy_hash="1"*64,
)))
check("Missing limit price blocked", blocked(lambda: create_order(
    order_id="BAD", timestamp="T", symbol="AAPL", side="BUY",
    order_type="LIMIT", time_in_force="DAY", quantity=1, strategy_hash="1"*64,
)))
check("Invalid quantity blocked", blocked(lambda: create_order(
    order_id="BAD", timestamp="T", symbol="AAPL", side="BUY",
    order_type="MARKET", time_in_force="DAY", quantity=0, strategy_hash="1"*64,
)))
check("Invalid strategy hash blocked", blocked(lambda: create_order(
    order_id="BAD", timestamp="T", symbol="AAPL", side="BUY",
    order_type="MARKET", time_in_force="DAY", quantity=1, strategy_hash="BAD",
)))
check("Duplicate bar timestamp blocked", blocked(lambda: simulate_execution(
    market, bars + (bars[0],), policy,
)))
check("Invalid participation rate blocked", blocked(lambda: ExecutionPolicy(max_participation_rate=Decimal("0"))))

tampered_order = replace(market, quantity=999)
check("Tampered order detected", blocked(lambda: verify_order(tampered_order)))

tampered_report = replace(market_report, filled_quantity=99)
check("Tampered execution report detected", blocked(lambda: verify_report(tampered_report)))

history = create_history((market_report, limit_report, ioc_report, fok_report, stop_report))
check("Execution history created", len(history.reports) == 5)
check("History hash verified", verify_history(history))
check("Duplicate report blocked", blocked(lambda: create_history((market_report, market_report))))

with tempfile.TemporaryDirectory() as folder:
    path = Path(folder) / "execution_history.json"
    save_history(history, path)
    loaded = load_history(path)
    check("Execution history save and load passed", loaded == history)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["reports"][0]["filled_quantity"] = 99
    path.write_text(json.dumps(payload), encoding="utf-8")
    check("Tampered saved execution history blocked", blocked(lambda: load_history(path)))

tree = ast.parse(Path(m.__file__).read_text(encoding="utf-8"))
forbidden = {"requests","urllib","httpx","aiohttp","socket","alpaca_trade_api","ib_insync","ccxt"}
imports=set()
for node in ast.walk(tree):
    if isinstance(node,ast.Import):
        imports.update(alias.name.split(".")[0] for alias in node.names)
    elif isinstance(node,ast.ImportFrom) and node.module:
        imports.add(node.module.split(".")[0])

check("Forbidden network/broker imports are absent", not(imports & forbidden))
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

print("="*116)
print("V28.9 offline execution simulator test completed successfully.")
print("Order queue, MARKET/LIMIT/STOP_LIMIT, DAY/IOC/FOK, partial fills, VWAP,")
print("slippage, commission, persistence, hashing, and tamper checks passed.")
print("Market/account/network/broker/order/live execution remained blocked.")
