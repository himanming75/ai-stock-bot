from dataclasses import replace
from decimal import Decimal
from pathlib import Path
import ast
import json
import tempfile

import backtest.offline_features_v27_0 as m
from backtest.offline_features_v27_0 import (
    FeatureError,
    FeaturePolicy,
    PriceBar,
    build_features,
    load_feature_set,
    save_feature_set,
    verify_feature_set,
    verify_row,
)


def check(name, condition):
    print(f"{name:<68}: {condition}")
    if not condition:
        raise AssertionError(name)


def blocked(fn):
    try:
        fn()
    except FeatureError:
        return True
    return False


def make_bars():
    bars = []
    close = Decimal("100")
    for index in range(60):
        if index < 30:
            close += Decimal("1")
        else:
            close += Decimal("0.5") if index % 2 == 0 else Decimal("-0.2")
        open_price = close - Decimal("0.3")
        bars.append(PriceBar(
            timestamp=f"2026-05-{index + 1:02d}T16:00:00+00:00",
            open=open_price,
            high=close + Decimal("1"),
            low=close - Decimal("1"),
            close=close,
            volume=Decimal("1000") + Decimal(index * 20),
        ))
    return tuple(bars)


policy = FeaturePolicy(
    sma_fast=5,
    sma_slow=20,
    ema_fast=12,
    ema_slow=26,
    rsi_period=14,
    macd_signal_period=9,
    atr_period=14,
    bollinger_period=20,
    roc_period=10,
    volatility_period=20,
    volume_period=20,
    breakout_period=20,
)

bars = make_bars()
features = build_features(bars, policy)
last = dict(features.rows[-1].features)

check("V27.0 engine version verified", m.VERSION == "27.0")
check("Feature set created", len(features.rows) == len(bars))
check("Feature schema created", len(features.feature_names) == 24)
check("SMA fast calculated", last["sma_fast"] is not None)
check("SMA slow calculated", last["sma_slow"] is not None)
check("EMA fast calculated", last["ema_fast"] is not None)
check("EMA slow calculated", last["ema_slow"] is not None)
check("RSI calculated", last["rsi"] is not None)
check("MACD calculated", last["macd"] is not None)
check("MACD signal calculated", last["macd_signal"] is not None)
check("MACD histogram calculated", last["macd_histogram"] is not None)
check("ATR calculated", last["atr"] is not None and last["atr"] > Decimal("0"))
check("Bollinger width calculated", last["bollinger_width"] is not None)
check("Bollinger z-score calculated", last["bollinger_zscore"] is not None)
check("ROC calculated", last["roc"] is not None)
check("Momentum calculated", last["momentum"] is not None)
check("Historical volatility calculated", last["historical_volatility"] is not None)
check("OBV calculated", last["obv"] is not None)
check("Relative volume calculated", last["relative_volume"] is not None)
check("Candle features calculated", all(last[name] is not None for name in (
    "candle_body_pct", "upper_wick_pct", "lower_wick_pct", "range_pct"
)))
check("Gap feature calculated", last["gap_pct"] is not None)
check("Breakout features calculated", last["breakout_up"] is not None and last["breakout_down"] is not None)
check("Trend strength calculated", last["trend_strength"] is not None)
check("Warmup values use None", dict(features.rows[0].features)["sma_slow"] is None)
check("Row hash verified", verify_row(features.rows[-1], features.feature_names))
check("Feature-set hash verified", verify_feature_set(features))
check("Deterministic output returned", features == build_features(bars, policy))

duplicate = bars + (bars[-1],)
check("Duplicate timestamp blocked", blocked(lambda: build_features(duplicate, policy)))
bad_order = tuple(reversed(bars))
check("Non-increasing timestamps blocked", blocked(lambda: build_features(bad_order, policy)))
bad_bar = replace(bars[0], high=Decimal("90"))
check("Invalid OHLC blocked", blocked(lambda: build_features((bad_bar,) + bars[1:], policy)))
check("Invalid policy blocked", blocked(lambda: FeaturePolicy(sma_fast=20, sma_slow=5)))

tampered_row = replace(features.rows[-1], close=Decimal("999"))
check("Tampered row detected", blocked(lambda: verify_row(tampered_row, features.feature_names)))

tampered_set = replace(features, feature_hash="BROKEN")
check("Tampered feature set detected", blocked(lambda: verify_feature_set(tampered_set)))

with tempfile.TemporaryDirectory() as folder:
    path = Path(folder) / "features.json"
    save_feature_set(features, path)
    loaded = load_feature_set(path)
    check("Feature set save and load passed", loaded == features)

    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["rows"][-1]["features"]["rsi"] = "999.0000"
    path.write_text(json.dumps(payload), encoding="utf-8")
    check("Tampered saved feature set blocked", blocked(lambda: load_feature_set(path)))

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

print("=" * 88)
print("V27.0 offline feature engineering test completed successfully.")
print("Trend, momentum, volatility, volume, candle, breakout, persistence,")
print("hashing, warmup handling, and tamper checks passed.")
print("Market/account/network/broker/order/live execution remained blocked.")
