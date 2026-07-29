from dataclasses import replace
from decimal import Decimal
from pathlib import Path
import ast
import json
import tempfile

import backtest.offline_split_engine_v27_3 as m
from backtest.offline_split_engine_v27_3 import (
    DatasetRow,
    SplitError,
    SplitPolicy,
    load_result,
    save_result,
    split_dataset,
    verify_result,
)


def check(name, condition):
    print(f"{name:<70}: {condition}")
    if not condition:
        raise AssertionError(name)


def blocked(fn):
    try:
        fn()
    except SplitError:
        return True
    return False


rows = tuple(
    DatasetRow(
        row_id=f"ROW-{index:03d}",
        timestamp=f"2026-07-{index + 1:02d}T16:00:00+00:00",
        features=(Decimal(index), Decimal(index + 1), Decimal(index + 2)),
        label=(-1 if index % 3 == 0 else 0 if index % 3 == 1 else 1),
    )
    for index in range(30)
)

stratified_policy = SplitPolicy(
    validation_ratio=Decimal("0.20"),
    mode="STRATIFIED",
    shuffle=True,
    random_seed=123,
)
stratified = split_dataset(rows, stratified_policy)

check("V27.3 engine version verified", m.VERSION == "27.3")
check("Stratified split created", stratified.mode == "STRATIFIED")
check("Train partition created", len(stratified.train_ids) > 0)
check("Validation partition created", len(stratified.validation_ids) > 0)
check("No train/validation leakage", not (set(stratified.train_ids) & set(stratified.validation_ids)))
check("Class counts created", len(stratified.class_counts) == 3)
check("Every class represented in train", all(item.train_count > 0 for item in stratified.class_counts))
check("Every class represented in validation", all(item.validation_count > 0 for item in stratified.class_counts))
check("Ratios sum to one", stratified.train_ratio + stratified.validation_ratio == Decimal("1.0000"))
check("Split hash verified", verify_result(stratified))
check("Deterministic split returned", stratified == split_dataset(rows, stratified_policy))

random_policy = SplitPolicy(
    validation_ratio=Decimal("0.25"),
    mode="RANDOM",
    shuffle=True,
    random_seed=99,
)
random_split = split_dataset(rows, random_policy)
check("Random split created", random_split.mode == "RANDOM")
check("Random split deterministic", random_split == split_dataset(rows, random_policy))

time_policy = SplitPolicy(
    validation_ratio=Decimal("0.20"),
    mode="TIME_SERIES",
    shuffle=False,
    purge_size=2,
)
time_split = split_dataset(rows, time_policy)
check("Time-series split created", time_split.mode == "TIME_SERIES")
check("Purge rows created", len(time_split.purged_ids) == 2)
check("Train rows precede validation rows", max(time_split.train_ids) < min(time_split.validation_ids))
check("Time-series leakage blocked", not (
    set(time_split.train_ids) & set(time_split.validation_ids)
    or set(time_split.train_ids) & set(time_split.purged_ids)
    or set(time_split.validation_ids) & set(time_split.purged_ids)
))

check("Invalid validation ratio blocked", blocked(lambda: SplitPolicy(validation_ratio=1)))
check("Invalid mode blocked", blocked(lambda: SplitPolicy(mode="BAD")))
check("Time-series shuffle blocked", blocked(lambda: SplitPolicy(mode="TIME_SERIES", shuffle=True)))
check("Duplicate row ID blocked", blocked(lambda: split_dataset(rows + (rows[0],), stratified_policy)))

bad_timestamp = replace(rows[1], timestamp=rows[0].timestamp)
check("Duplicate timestamp blocked", blocked(lambda: split_dataset((rows[0], bad_timestamp) + rows[2:], stratified_policy)))

bad_features = replace(rows[0], features=())
check("Empty features blocked", blocked(lambda: split_dataset((bad_features,) + rows[1:], stratified_policy)))

tampered = replace(stratified, train_ids=stratified.train_ids + (stratified.validation_ids[0],))
check("Tampered split detected", blocked(lambda: verify_result(tampered)))

with tempfile.TemporaryDirectory() as folder:
    path = Path(folder) / "split.json"
    save_result(stratified, path)
    loaded = load_result(path)
    check("Split save and load passed", loaded == stratified)

    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["validation_ratio"] = "0.9000"
    path.write_text(json.dumps(payload), encoding="utf-8")
    check("Tampered saved split blocked", blocked(lambda: load_result(path)))

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
print("V27.3 offline train/validation split test completed successfully.")
print("Random, stratified, time-series, purge, class-balance, persistence,")
print("hashing, deterministic output, leakage, and tamper checks passed.")
print("Market/account/network/broker/order/live execution remained blocked.")
