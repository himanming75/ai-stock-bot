from dataclasses import replace
from datetime import datetime, timedelta, timezone
import ast
import json
from pathlib import Path
import tempfile

from backtest.offline_multi_signal_v25_1 import (
    VERSION, FORBIDDEN_CAPABILITIES, MultiSignalPolicy, OfflineMultiSignalEngine,
    PriceBar, load_result, save_result, verify_result,
)


def bars(kind: str, count: int = 90):
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    out = []
    price = 100.0
    for i in range(count):
        if kind == "up": price *= 1.006
        elif kind == "down": price *= 0.994
        else: price *= 1.0 + (0.001 if i % 2 == 0 else -0.001)
        o = price * (0.998 if kind != "down" else 1.002)
        c = price
        out.append(PriceBar((start + timedelta(days=i)).isoformat(), o,
                            max(o, c) * 1.004, min(o, c) * 0.996, c,
                            100000 + i * 500))
    return out


def check(label, value):
    print(f"{label:<52}: {bool(value)}")
    assert value


def main():
    engine = OfflineMultiSignalEngine(MultiSignalPolicy(buy_threshold=0.18, sell_threshold=-0.18))
    at = "2026-07-28T20:00:00+00:00"
    buy = engine.evaluate("TEST", bars("up"), evaluated_at=at)
    sell = engine.evaluate("TEST", bars("down"), evaluated_at=at)
    hold = engine.evaluate("TEST", bars("flat"), evaluated_at=at)

    check("V25.1 engine version verified", buy.version == VERSION == "25.1")
    check("BUY signal generated", buy.action == "BUY")
    check("SELL signal generated", sell.action == "SELL")
    check("HOLD signal generated", hold.action == "HOLD")
    check("RSI calculated", 0 <= buy.indicators.rsi <= 100)
    check("MACD calculated", isinstance(buy.indicators.macd_histogram, float))
    check("ATR calculated", buy.indicators.atr > 0)
    check("Bollinger Bands calculated", buy.indicators.bollinger_lower < buy.indicators.bollinger_upper)
    check("Stochastic calculated", 0 <= buy.indicators.stochastic_k <= 100)
    check("OBV calculated", isinstance(buy.indicators.obv, float))
    check("Bullish consensus detected", buy.consensus.direction == "BULLISH")
    check("Bearish consensus detected", sell.consensus.direction == "BEARISH")
    check("Result hash verified", verify_result(buy) and verify_result(sell) and verify_result(hold))
    check("Deterministic result verified", buy == engine.evaluate("TEST", bars("up"), evaluated_at=at))
    check("Confidence is bounded", 0 <= buy.confidence <= 1)

    low_volume = [replace(b, volume=0.0) for b in bars("up")]
    gated = OfflineMultiSignalEngine(MultiSignalPolicy(min_volume=1.0, buy_threshold=0.18)).evaluate("TEST", low_volume, evaluated_at=at)
    check("Low-volume policy forced HOLD", gated.action == "HOLD")

    volatile = bars("up")
    volatile[-1] = replace(volatile[-1], open=volatile[-2].close * 1.50,
                           high=volatile[-2].close * 1.55, low=volatile[-2].close * 1.45,
                           close=volatile[-2].close * 1.50)
    guarded = engine.evaluate("TEST", volatile, evaluated_at=at)
    check("Abnormal return guard forced HOLD", guarded.action == "HOLD")

    check("Tampered result detected", not verify_result(replace(buy, score=buy.score + 0.1)))
    try:
        MultiSignalPolicy(fast_ema=30, slow_ema=20).validate(); bad_policy = False
    except ValueError: bad_policy = True
    check("Invalid policy was blocked", bad_policy)

    bad = bars("flat")
    bad[5] = replace(bad[5], timestamp=bad[4].timestamp)
    try:
        engine.evaluate("TEST", bad, evaluated_at=at); bad_time = False
    except ValueError: bad_time = True
    check("Non-increasing timestamps were blocked", bad_time)

    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "result.json"
        save_result(buy, p)
        loaded = load_result(p)
        check("Result save and load passed", loaded == buy)
        data = json.loads(p.read_text(encoding="utf-8")); data["score"] += 0.2
        p.write_text(json.dumps(data), encoding="utf-8")
        try: load_result(p); tampered_file = False
        except ValueError: tampered_file = True
        check("Tampered saved result was blocked", tampered_file)

    source = Path("backtest/offline_multi_signal_v25_1.py").read_text(encoding="utf-8")
    imports = {n.names[0].name.split('.')[0] for n in ast.walk(ast.parse(source)) if isinstance(n, ast.Import)}
    imports |= {n.module.split('.')[0] for n in ast.walk(ast.parse(source)) if isinstance(n, ast.ImportFrom) and n.module}
    forbidden = {"requests", "httpx", "urllib", "socket", "alpaca", "ibapi", "ccxt", "yfinance"}
    check("Forbidden network/broker imports are absent", imports.isdisjoint(forbidden))
    check("Market data API was not called", not FORBIDDEN_CAPABILITIES["market_data_api"])
    check("Account API was not called", not FORBIDDEN_CAPABILITIES["account_api"])
    check("Network was not accessed", not FORBIDDEN_CAPABILITIES["network_access"])
    check("Broker API was not called", not FORBIDDEN_CAPABILITIES["broker_api"])
    check("Broker order was not created", not FORBIDDEN_CAPABILITIES["order_creation"])
    check("Order was not submitted", not FORBIDDEN_CAPABILITIES["order_submission"])
    check("Live execution not authorized", not FORBIDDEN_CAPABILITIES["live_execution"])
    check("Funds were not reserved", not FORBIDDEN_CAPABILITIES["fund_reservation"])
    check("Holdings were not reserved", not FORBIDDEN_CAPABILITIES["holding_reservation"])
    check("All checks passed", True)
    print("=" * 72)
    print("V25.1 offline multi-indicator signal engine test completed successfully.")
    print("RSI, MACD, ATR, Bollinger, stochastic, OBV, consensus, and safety gates were verified.")
    print("Market/account/network/broker/order/live execution remained blocked.")


if __name__ == "__main__":
    main()
