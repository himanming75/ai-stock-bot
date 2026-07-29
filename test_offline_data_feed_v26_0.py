from dataclasses import replace
from decimal import Decimal
from pathlib import Path
import ast
import csv
import json
import tempfile

import backtest.offline_data_feed_v26_0 as m
from backtest.offline_data_feed_v26_0 import (
    DataFeedError,
    MarketBar,
    bars_for_symbol,
    create_dataset,
    detect_missing_bars,
    forward_fill_missing,
    load_csv,
    load_dataset,
    resample,
    save_dataset,
    verify_dataset,
)


def check(name, condition):
    print(f"{name:<58}: {condition}")
    if not condition:
        raise AssertionError(name)


def blocked(fn):
    try:
        fn()
    except DataFeedError:
        return True
    return False


bars = (
    MarketBar("AAPL", "2026-01-01T14:30:00+00:00", 100, 101, 99, 100.5, 1000),
    MarketBar("AAPL", "2026-01-01T14:31:00+00:00", 100.5, 102, 100, 101.5, 1200),
    MarketBar("AAPL", "2026-01-01T14:33:00+00:00", 101.5, 103, 101, 102.5, 900),
    MarketBar("AAPL", "2026-01-01T14:34:00+00:00", 102.5, 104, 102, 103.5, 1100),
    MarketBar("MSFT", "2026-01-01T14:30:00+00:00", 200, 201, 199, 200.5, 1500),
    MarketBar("MSFT", "2026-01-01T14:31:00+00:00", 200.5, 202, 200, 201.5, 1600),
    MarketBar("MSFT", "2026-01-01T14:32:00+00:00", 201.5, 203, 201, 202.5, 1700),
    MarketBar("MSFT", "2026-01-01T14:33:00+00:00", 202.5, 204, 202, 203.5, 1800),
)

dataset = create_dataset(bars, 1)
missing = detect_missing_bars(dataset)
filled = forward_fill_missing(dataset)
resampled = resample(filled, 2)

check("V26.0 engine version verified", m.VERSION == "26.0")
check("Multi-symbol dataset created", dataset.symbols == ("AAPL", "MSFT"))
check("Dataset hash verified", verify_dataset(dataset))
check("AAPL bars filtered", len(bars_for_symbol(dataset, "AAPL")) == 4)
check("Missing AAPL bar detected", len(missing["AAPL"]) == 1)
check("MSFT has no missing bars", len(missing["MSFT"]) == 0)
check("Forward fill inserted one bar", len(filled.bars) == len(dataset.bars) + 1)
check("Forward-filled volume is zero", any(
    bar.symbol == "AAPL"
    and bar.timestamp.startswith("2026-01-01T14:32:00")
    and bar.volume == Decimal("0.000000")
    for bar in filled.bars
))
check("Two-minute resample created", resampled.timeframe_minutes == 2)
check("Resample aggregated OHLCV", len(resampled.bars) == 4)
check("Deterministic dataset returned", dataset == create_dataset(bars, 1))

duplicate = bars + (bars[0],)
check("Duplicate bar blocked", blocked(lambda: create_dataset(duplicate, 1)))
bad_bar = replace(bars[0], high=Decimal("90"))
check("Invalid OHLC blocked", blocked(lambda: create_dataset((bad_bar,), 1)))
check("Invalid timeframe blocked", blocked(lambda: create_dataset(bars, 0)))
check("Invalid resample ratio blocked", blocked(lambda: resample(resampled, 3)))

tampered = replace(dataset, timeframe_minutes=5)
check("Tampered dataset detected", blocked(lambda: verify_dataset(tampered)))

with tempfile.TemporaryDirectory() as folder:
    folder = Path(folder)

    csv_path = folder / "data.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "symbol", "timestamp", "open", "high", "low", "close", "volume"
        ])
        writer.writeheader()
        for bar in bars:
            writer.writerow({
                "symbol": bar.symbol,
                "timestamp": bar.timestamp,
                "open": bar.open,
                "high": bar.high,
                "low": bar.low,
                "close": bar.close,
                "volume": bar.volume,
            })

    csv_dataset = load_csv(csv_path, 1)
    check("CSV load passed", csv_dataset == dataset)

    save_path = folder / "dataset.json"
    save_dataset(dataset, save_path)
    loaded = load_dataset(save_path)
    check("Dataset save and load passed", loaded == dataset)

    payload = json.loads(save_path.read_text(encoding="utf-8"))
    payload["bars"][0]["close"] = "999.00"
    save_path.write_text(json.dumps(payload), encoding="utf-8")
    check("Tampered saved dataset blocked", blocked(lambda: load_dataset(save_path)))

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
print("V26.0 offline data feed engine test completed successfully.")
print("CSV loading, multi-symbol validation, missing-bar detection, forward fill,")
print("timeframe aggregation, persistence, hashing, and tamper checks passed.")
print("Market/account/network/broker/order/live execution remained blocked.")
