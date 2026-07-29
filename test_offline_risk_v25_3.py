from dataclasses import replace
from decimal import Decimal
from pathlib import Path
import ast, json, tempfile

import backtest.offline_risk_v25_3 as m
from backtest.offline_risk_v25_3 import (
    PositionRisk, RiskDecision, RiskError, RiskPolicy, RiskRequest,
    calculate_position_size, evaluate_trade, load_decision,
    save_decision, update_protective_stop, verify_decision,
)


def check(name, condition):
    print(f"{name:<56}: {condition}")
    if not condition:
        raise AssertionError(name)


def blocked(fn):
    try:
        fn()
    except RiskError:
        return True
    return False


policy = RiskPolicy(
    risk_per_trade_pct=Decimal("0.01"),
    max_daily_loss_pct=Decimal("0.03"),
    max_position_pct=Decimal("0.30"),
    max_sector_pct=Decimal("0.35"),
    max_open_positions=3,
    stop_atr_multiple=Decimal("2"),
    take_profit_r_multiple=Decimal("2"),
    trailing_stop_atr_multiple=Decimal("2.5"),
    break_even_r_multiple=Decimal("1"),
    min_reward_risk=Decimal("1.5"),
)

request = RiskRequest(
    symbol="AAPL",
    sector="Technology",
    entry_price=Decimal("100"),
    atr=Decimal("2"),
    account_equity=Decimal("100000"),
    available_cash=Decimal("50000"),
    current_daily_pnl=Decimal("-500"),
    open_positions=(),
)
decision = evaluate_trade(request, policy)

check("V25.3 engine version verified", m.VERSION == "25.3")
check("Trade was approved", decision.approved)
check("ATR stop was calculated", decision.stop_price == Decimal("96.00"))
check("Take-profit was calculated", decision.take_profit_price == Decimal("108.00"))
check("Risk-based quantity was calculated", decision.quantity == Decimal("250.000000"))
check("Risk amount equals policy risk", decision.risk_amount == Decimal("1000.00"))
check("Reward/risk ratio was calculated", decision.reward_risk_ratio == Decimal("2.0000"))
check("Trailing distance was calculated", decision.trailing_stop_distance == Decimal("5.00"))
check("Break-even trigger was calculated", decision.break_even_trigger == Decimal("104.00"))
check("Decision hash verified", verify_decision(decision))
check("Deterministic decision returned", decision == evaluate_trade(request, policy))

size = calculate_position_size(100000, Decimal("0.01"), 100, 96)
check("Standalone position sizing passed", size == Decimal("250.000000"))

daily_loss_request = replace(request, current_daily_pnl=Decimal("-3000"))
daily_loss_decision = evaluate_trade(daily_loss_request, policy)
check("Daily loss limit blocked trade", "DAILY_LOSS_LIMIT" in daily_loss_decision.reason_codes)

positions = (
    PositionRisk("MSFT", "TECHNOLOGY", Decimal("100"), Decimal("200"), Decimal("200"), Decimal("190")),
    PositionRisk("NVDA", "TECHNOLOGY", Decimal("100"), Decimal("150"), Decimal("150"), Decimal("140")),
    PositionRisk("JPM", "FINANCIALS", Decimal("50"), Decimal("200"), Decimal("200"), Decimal("190")),
)
max_positions_decision = evaluate_trade(replace(request, open_positions=positions), policy)
check("Maximum open positions blocked trade", "MAX_OPEN_POSITIONS" in max_positions_decision.reason_codes)

sector_heavy = (
    PositionRisk("MSFT", "TECHNOLOGY", Decimal("100"), Decimal("200"), Decimal("200"), Decimal("190")),
)
sector_decision = evaluate_trade(replace(request, open_positions=sector_heavy), policy)
check("Sector exposure blocked trade", "MAX_SECTOR_PCT" in sector_decision.reason_codes)

low_cash_decision = evaluate_trade(replace(request, available_cash=Decimal("0.00")), policy)
check("Insufficient cash produced zero quantity", "ZERO_QUANTITY" in low_cash_decision.reason_codes)

bad_stop_request = replace(request, entry_price=Decimal("3"), atr=Decimal("2"))
bad_stop_decision = evaluate_trade(bad_stop_request, policy)
check("Invalid ATR stop blocked trade", "INVALID_STOP" in bad_stop_decision.reason_codes)

updated_stop = update_protective_stop(
    entry_price=100,
    current_price=110,
    current_stop=96,
    atr=2,
    trailing_atr_multiple=Decimal("2.5"),
    break_even_r_multiple=1,
    initial_risk_per_share=4,
)
check("Trailing stop advanced", updated_stop == Decimal("105.00"))

break_even_stop = update_protective_stop(
    entry_price=100,
    current_price=104,
    current_stop=96,
    atr=5,
    trailing_atr_multiple=Decimal("2.5"),
    break_even_r_multiple=1,
    initial_risk_per_share=4,
)
check("Break-even stop activated", break_even_stop == Decimal("100.00"))

tampered = replace(decision, quantity=decision.quantity + Decimal("1"))
check("Tampered decision was detected", blocked(lambda: verify_decision(tampered)))

invalid_policy = lambda: RiskPolicy(risk_per_trade_pct=Decimal("0"))
check("Invalid policy was blocked", blocked(invalid_policy))

with tempfile.TemporaryDirectory() as folder:
    path = Path(folder) / "risk_decision.json"
    save_decision(decision, path)
    loaded = load_decision(path)
    check("Decision save and load passed", loaded == decision)
    data = json.loads(path.read_text(encoding="utf-8"))
    data["quantity"] = "999999"
    path.write_text(json.dumps(data), encoding="utf-8")
    check("Tampered saved decision was blocked", blocked(lambda: load_decision(path)))

tree = ast.parse(Path(m.__file__).read_text(encoding="utf-8"))
forbidden = {
    "requests", "urllib", "httpx", "aiohttp", "socket",
    "alpaca_trade_api", "ib_insync", "ccxt"
}
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

print("=" * 76)
print("V25.3 offline risk manager test completed successfully.")
print("Position sizing, ATR stops, take-profit, trailing/break-even stops,")
print("daily loss, position count, sector exposure, persistence, and tamper checks passed.")
print("Market/account/network/broker/order/live execution remained blocked.")
