from dataclasses import replace
from decimal import Decimal
from pathlib import Path
import ast
import json
import tempfile

import backtest.offline_normalizer_v27_4 as m
from backtest.offline_normalizer_v27_4 import (
    DataRow,
    NormalizationError,
    NormalizationPolicy,
    fit_normalizer,
    load_fitted,
    load_result,
    save_fitted,
    save_result,
    transform_rows,
    verify_fitted,
    verify_result,
)


def check(name, condition):
    print(f"{name:<72}: {condition}")
    if not condition:
        raise AssertionError(name)


def blocked(fn):
    try:
        fn()
    except NormalizationError:
        return True
    return False


train_rows = (
    DataRow("R1", (1, 10, 100)),
    DataRow("R2", (2, 20, 110)),
    DataRow("R3", (3, None, 120)),
    DataRow("R4", (4, 40, 130)),
    DataRow("R5", (100, 50, 140)),
)

validation_rows = (
    DataRow("V1", (5, 25, 115)),
    DataRow("V2", (6, None, 125)),
)

z_policy = NormalizationPolicy(
    method="ZSCORE",
    missing_strategy="MEDIAN",
    winsor_lower_pct=Decimal("0"),
    winsor_upper_pct=Decimal("80"),
    log_transform=False,
)
z_fit = fit_normalizer(train_rows, z_policy)
z_output = transform_rows(validation_rows, z_fit)

check("V27.4 engine version verified", m.VERSION == "27.4")
check("Z-score fit created", z_fit.method == "ZSCORE")
check("Feature statistics created", len(z_fit.stats) == 3)
check("Median missing fill calculated", z_fit.stats[1].fill_value == Decimal("30.0000"))
check("Winsor upper clip calculated", z_fit.stats[0].upper_clip < Decimal("100"))
check("Validation rows transformed", len(z_output.rows) == 2)
check("Missing validation value filled", all(value is not None for value in z_output.rows[1].values))
check("Fit hash verified", verify_fitted(z_fit))
check("Output hash verified", verify_result(z_output))
check("Deterministic fit returned", z_fit == fit_normalizer(train_rows, z_policy))
check("Deterministic transform returned", z_output == transform_rows(validation_rows, z_fit))

minmax_policy = NormalizationPolicy(
    method="MINMAX",
    missing_strategy="MEAN",
)
minmax_fit = fit_normalizer(train_rows, minmax_policy)
minmax_output = transform_rows(validation_rows, minmax_fit)
check("Min-max fit created", minmax_fit.method == "MINMAX")
check("Min-max values bounded", all(
    Decimal("0") <= value <= Decimal("1")
    for row in minmax_output.rows
    for value in row.values
))

robust_policy = NormalizationPolicy(
    method="ROBUST",
    missing_strategy="ZERO",
)
robust_fit = fit_normalizer(train_rows, robust_policy)
robust_output = transform_rows(validation_rows, robust_fit)
check("Robust fit created", robust_fit.method == "ROBUST")
check("Robust values calculated", all(isinstance(value, Decimal) for row in robust_output.rows for value in row.values))

log_rows = (
    DataRow("L1", (1, 10)),
    DataRow("L2", (2, 20)),
    DataRow("L3", (3, 30)),
)
log_policy = NormalizationPolicy(method="ZSCORE", log_transform=True, log_offset=1)
log_fit = fit_normalizer(log_rows, log_policy)
log_output = transform_rows(log_rows, log_fit)
check("Log transform completed", len(log_output.rows) == 3)

check("Invalid method blocked", blocked(lambda: NormalizationPolicy(method="BAD")))
check("Invalid winsor percentiles blocked", blocked(lambda: NormalizationPolicy(
    winsor_lower_pct=90,
    winsor_upper_pct=10,
)))
check("Duplicate row ID blocked", blocked(lambda: fit_normalizer(train_rows + (train_rows[0],), z_policy)))
check("Inconsistent feature count blocked", blocked(lambda: fit_normalizer(
    train_rows + (DataRow("BAD", (1, 2)),),
    z_policy,
)))
check("All-missing feature blocked", blocked(lambda: fit_normalizer(
    (
        DataRow("M1", (1, None)),
        DataRow("M2", (2, None)),
    ),
    z_policy,
)))
check("ERROR missing strategy blocked", blocked(lambda: fit_normalizer(
    train_rows,
    replace(z_policy, missing_strategy="ERROR"),
)))
check("Mismatched transform feature count blocked", blocked(lambda: transform_rows(
    (DataRow("X", (1, 2)),),
    z_fit,
)))

tampered_fit = replace(z_fit, feature_count=99)
check("Tampered fit detected", blocked(lambda: verify_fitted(tampered_fit)))

tampered_row = replace(z_output.rows[0], values=(Decimal("999"),) + z_output.rows[0].values[1:])
tampered_output = replace(z_output, rows=(tampered_row,) + z_output.rows[1:])
check("Tampered normalized row detected", blocked(lambda: verify_result(tampered_output)))

with tempfile.TemporaryDirectory() as folder:
    folder = Path(folder)
    fit_path = folder / "normalizer.json"
    output_path = folder / "normalized.json"

    save_fitted(z_fit, fit_path)
    loaded_fit = load_fitted(fit_path)
    check("Fitted normalizer save and load passed", loaded_fit == z_fit)

    save_result(z_output, output_path)
    loaded_output = load_result(output_path)
    check("Normalized set save and load passed", loaded_output == z_output)

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    payload["rows"][0]["values"][0] = "999.0000"
    output_path.write_text(json.dumps(payload), encoding="utf-8")
    check("Tampered saved normalized set blocked", blocked(lambda: load_result(output_path)))

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

print("=" * 92)
print("V27.4 offline data normalization test completed successfully.")
print("Z-score, min-max, robust scaling, missing-value handling, winsorization,")
print("log transform, fit/transform separation, hashing, and tamper checks passed.")
print("Market/account/network/broker/order/live execution remained blocked.")
