from dataclasses import replace
from decimal import Decimal
from pathlib import Path
import ast, json, tempfile

import backtest.offline_strategy_v25_4 as m
from backtest.offline_strategy_v25_4 import (
    StrategyError, StrategyInput, StrategyPolicy,
    evaluate_strategies, load_decision, save_decision, verify_decision,
)


def check(name, condition):
    print(f"{name:<58}: {condition}")
    if not condition:
        raise AssertionError(name)


def blocked(fn):
    try:
        fn()
    except StrategyError:
        return True
    return False


policy = StrategyPolicy(
    trend_weight=Decimal("0.35"),
    momentum_weight=Decimal("0.30"),
    mean_reversion_weight=Decimal("0.10"),
    breakout_weight=Decimal("0.25"),
    buy_threshold=Decimal("0.20"),
    sell_threshold=Decimal("-0.20"),
    min_confidence=Decimal("0.35"),
)

bullish = StrategyInput(
    symbol="AAPL",
    close=Decimal("110"),
    ema_fast=Decimal("108"),
    ema_slow=Decimal("102"),
    rsi=Decimal("55"),
    macd=Decimal("2.5"),
    macd_signal=Decimal("1.0"),
    atr=Decimal("2"),
    highest_high=Decimal("110"),
    lowest_low=Decimal("95"),
    volume_ratio=Decimal("1.8"),
    return_5=Decimal("0.04"),
    return_20=Decimal("0.10"),
)
buy_decision = evaluate_strategies(bullish, policy)

bearish = StrategyInput(
    symbol="MSFT",
    close=Decimal("90"),
    ema_fast=Decimal("92"),
    ema_slow=Decimal("100"),
    rsi=Decimal("48"),
    macd=Decimal("-2.5"),
    macd_signal=Decimal("-0.5"),
    atr=Decimal("2"),
    highest_high=Decimal("110"),
    lowest_low=Decimal("90"),
    volume_ratio=Decimal("1.7"),
    return_5=Decimal("-0.05"),
    return_20=Decimal("-0.12"),
)
sell_decision = evaluate_strategies(bearish, policy)

neutral = StrategyInput(
    symbol="TSLA",
    close=Decimal("100"),
    ema_fast=Decimal("100.2"),
    ema_slow=Decimal("100"),
    rsi=Decimal("50"),
    macd=Decimal("0.1"),
    macd_signal=Decimal("0.1"),
    atr=Decimal("3"),
    highest_high=Decimal("110"),
    lowest_low=Decimal("90"),
    volume_ratio=Decimal("0.9"),
    return_5=Decimal("0"),
    return_20=Decimal("0"),
)
hold_decision = evaluate_strategies(neutral, policy)

conflict = StrategyInput(
    symbol="NVDA",
    close=Decimal("100"),
    ema_fast=Decimal("105"),
    ema_slow=Decimal("100"),
    rsi=Decimal("82"),
    macd=Decimal("1"),
    macd_signal=Decimal("0"),
    atr=Decimal("2"),
    highest_high=Decimal("110"),
    lowest_low=Decimal("90"),
    volume_ratio=Decimal("1"),
    return_5=Decimal("0.02"),
    return_20=Decimal("0.05"),
)
conflict_decision = evaluate_strategies(conflict, policy)

check("V25.4 engine version verified", m.VERSION == "25.4")
check("Bullish strategy produced BUY", buy_decision.action == "BUY")
check("Bearish strategy produced SELL", sell_decision.action == "SELL")
check("Neutral strategy produced HOLD", hold_decision.action == "HOLD")
check("Four strategy votes were generated", len(buy_decision.votes) == 4)
check("Trend vote was calculated", any(v.name == "TREND" for v in buy_decision.votes))
check("Momentum vote was calculated", any(v.name == "MOMENTUM" for v in buy_decision.votes))
check("Mean-reversion vote was calculated", any(v.name == "MEAN_REVERSION" for v in buy_decision.votes))
check("Breakout vote was calculated", any(v.name == "BREAKOUT" for v in buy_decision.votes))
check("Composite score is bounded", abs(buy_decision.composite_score) <= Decimal("1"))
check("Confidence is bounded", Decimal("0") <= buy_decision.confidence <= Decimal("1"))
check("Conflict was detected", conflict_decision.conflict_detected)
check("Conflict reason was recorded", "STRATEGY_CONFLICT" in conflict_decision.reason_codes)
check("Decision hash verified", verify_decision(buy_decision))
check("Deterministic decision returned", buy_decision == evaluate_strategies(bullish, policy))

low_conf_policy = replace(policy, min_confidence=Decimal("0.99"))
low_conf_decision = evaluate_strategies(bullish, low_conf_policy)
check("Low confidence gate forced HOLD", low_conf_decision.action == "HOLD")
check("Low confidence reason recorded", "LOW_CONFIDENCE" in low_conf_decision.reason_codes)

bad_rsi = replace(bullish, rsi=Decimal("101"))
check("Invalid RSI was blocked", blocked(lambda: evaluate_strategies(bad_rsi, policy)))

bad_range = replace(bullish, highest_high=Decimal("90"), lowest_low=Decimal("100"))
check("Invalid price range was blocked", blocked(lambda: evaluate_strategies(bad_range, policy)))

tampered = replace(buy_decision, composite_score=buy_decision.composite_score + Decimal("0.1"))
check("Tampered decision was detected", blocked(lambda: verify_decision(tampered)))

invalid_policy = lambda: StrategyPolicy(
    trend_weight=Decimal("-1"),
    momentum_weight=Decimal("1"),
)
check("Invalid policy was blocked", blocked(invalid_policy))

with tempfile.TemporaryDirectory() as folder:
    path = Path(folder) / "strategy.json"
    save_decision(buy_decision, path)
    loaded = load_decision(path)
    check("Decision save and load passed", loaded == buy_decision)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["action"] = "SELL"
    path.write_text(json.dumps(payload), encoding="utf-8")
    check("Tampered saved decision was blocked", blocked(lambda: load_decision(path)))

tree = ast.parse(Path(m.__file__).read_text(encoding="utf-8"))
forbidden = {
    "requests", "urllib", "httpx", "aiohttp", "socket",
    "alpaca_trade_api", "ib_insync", "ccxt",
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

print("=" * 78)
print("V25.4 offline strategy engine test completed successfully.")
print("Trend, momentum, mean-reversion, breakout, weighting, conflict resolution,")
print("confidence gating, persistence, hashing, and tamper detection were verified.")
print("Market/account/network/broker/order/live execution remained blocked.")
