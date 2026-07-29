from dataclasses import replace
from decimal import Decimal
from pathlib import Path
import ast
import json
import tempfile

import backtest.offline_label_generator_v27_2 as m
from backtest.offline_label_generator_v27_2 import (
    LabelError,
    LabelPolicy,
    PricePoint,
    align_features_and_labels,
    generate_labels,
    load_label_set,
    save_label_set,
    verify_label_set,
    verify_row,
)


def check(name, condition):
    print(f"{name:<70}: {condition}")
    if not condition:
        raise AssertionError(name)


def blocked(fn):
    try:
        fn()
    except LabelError:
        return True
    return False


prices = [
    100, 101, 103, 106, 108, 104, 101, 98, 95, 96,
    100, 105, 111, 108, 104, 99, 94, 92, 96, 101,
    107, 112, 109, 105, 100, 97, 93, 96, 102, 108,
]
points = tuple(
    PricePoint(
        timestamp=f"2026-06-{index + 1:02d}T16:00:00+00:00",
        close=Decimal(str(price)),
        high=Decimal(str(price)) + Decimal("1.5"),
        low=Decimal(str(price)) - Decimal("1.5"),
    )
    for index, price in enumerate(prices)
)

policy = LabelPolicy(
    horizon_bars=3,
    buy_threshold_pct=Decimal("2"),
    sell_threshold_pct=Decimal("-2"),
    strong_buy_threshold_pct=Decimal("5"),
    strong_sell_threshold_pct=Decimal("-5"),
    use_strong_labels=True,
    take_profit_pct=Decimal("3"),
    stop_loss_pct=Decimal("2"),
    barrier_mode=True,
    tie_breaker="STOP_FIRST",
    drop_incomplete_horizon=True,
)

labels = generate_labels(points, policy)
label_names = {row.label for row in labels.rows}

check("V27.2 engine version verified", m.VERSION == "27.2")
check("Label rows were generated", len(labels.rows) == len(points) - policy.horizon_bars)
check("BUY or STRONG_BUY labels generated", bool(label_names & {"BUY", "STRONG_BUY"}))
check("SELL or STRONG_SELL labels generated", bool(label_names & {"SELL", "STRONG_SELL"}))
flat_points = tuple(
    PricePoint(
        timestamp=f"2026-08-{index + 1:02d}T16:00:00+00:00",
        close=Decimal("100"),
        high=Decimal("100.5"),
        low=Decimal("99.5"),
    )
    for index in range(8)
)
flat_labels = generate_labels(
    flat_points,
    replace(
        policy,
        barrier_mode=False,
        buy_threshold_pct=Decimal("2"),
        sell_threshold_pct=Decimal("-2"),
        strong_buy_threshold_pct=Decimal("5"),
        strong_sell_threshold_pct=Decimal("-5"),
    ),
)
check("HOLD labels generated", all(row.label == "HOLD" for row in flat_labels.rows))
check("Future return calculated", isinstance(labels.rows[0].future_return_pct, Decimal))
check("Maximum favorable excursion calculated", labels.rows[0].max_favorable_excursion_pct is not None)
check("Maximum adverse excursion calculated", labels.rows[0].max_adverse_excursion_pct is not None)
check("Label codes generated", all(row.label_code in {-2, -1, 0, 1, 2} for row in labels.rows))
check("Incomplete horizon rows dropped", all(row.horizon_complete for row in labels.rows))
check("Class distribution created", sum(stat.count for stat in labels.class_distribution) == len(labels.rows))
check("Imbalance ratio calculated", labels.imbalance_ratio >= Decimal("1"))
check("Row hash verified", verify_row(labels.rows[0]))
check("Label-set hash verified", verify_label_set(labels))
check("Deterministic output returned", labels == generate_labels(points, policy))

feature_times = [point.timestamp for point in points]
aligned = align_features_and_labels(feature_times, labels)
check("Feature-label alignment passed", len(aligned) == len(labels.rows))
check("Alignment excludes future-only rows", aligned[-1][0] == labels.rows[-1].timestamp)

non_barrier_policy = replace(policy, barrier_mode=False)
return_labels = generate_labels(points, non_barrier_policy)
check("Future-return mode generated labels", len(return_labels.rows) == len(labels.rows))

partial_policy = replace(policy, drop_incomplete_horizon=False)
partial = generate_labels(points, partial_policy)
check("Incomplete horizon can be retained", len(partial.rows) == len(points) - 1)
check("Incomplete rows marked correctly", any(not row.horizon_complete for row in partial.rows))

tie_points = (
    PricePoint("2026-07-01T16:00:00+00:00", 100, 101, 99),
    PricePoint("2026-07-02T16:00:00+00:00", 100, 104, 96),
    PricePoint("2026-07-03T16:00:00+00:00", 100, 101, 99),
)
tie_stop = generate_labels(
    tie_points,
    LabelPolicy(
        horizon_bars=1,
        take_profit_pct=3,
        stop_loss_pct=3,
        tie_breaker="STOP_FIRST",
        drop_incomplete_horizon=True,
    ),
)
check("STOP_FIRST tie-breaker applied", tie_stop.rows[0].label in {"SELL", "STRONG_SELL"})

duplicate = points + (points[-1],)
check("Duplicate timestamp blocked", blocked(lambda: generate_labels(duplicate, policy)))
check("Non-increasing timestamps blocked", blocked(lambda: generate_labels(tuple(reversed(points)), policy)))
bad_point = replace(points[0], high=Decimal("90"))
check("Invalid price range blocked", blocked(lambda: generate_labels((bad_point,) + points[1:], policy)))
check("Invalid policy blocked", blocked(lambda: LabelPolicy(horizon_bars=0)))
check("Duplicate feature timestamps blocked", blocked(lambda: align_features_and_labels(
    [labels.rows[0].timestamp, labels.rows[0].timestamp],
    labels,
)))

tampered_row = replace(labels.rows[0], label_code=999)
check("Tampered label row detected", blocked(lambda: verify_row(tampered_row)))

tampered_set = replace(labels, imbalance_ratio=Decimal("999"))
check("Tampered label set detected", blocked(lambda: verify_label_set(tampered_set)))

with tempfile.TemporaryDirectory() as folder:
    path = Path(folder) / "labels.json"
    save_label_set(labels, path)
    loaded = load_label_set(path)
    check("Label set save and load passed", loaded == labels)

    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["rows"][0]["label"] = "HOLD"
    path.write_text(json.dumps(payload), encoding="utf-8")
    check("Tampered saved label set blocked", blocked(lambda: load_label_set(path)))

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

print("=" * 90)
print("V27.2 offline label generator test completed successfully.")
print("Future-return labels, barriers, strong labels, leakage-safe alignment,")
print("distribution, persistence, hashing, and tamper checks passed.")
print("Market/account/network/broker/order/live execution remained blocked.")
