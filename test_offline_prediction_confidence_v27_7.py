from dataclasses import replace
from decimal import Decimal
from pathlib import Path
import ast
import csv
import json
import tempfile

import backtest.offline_prediction_confidence_v27_7 as m
from backtest.offline_prediction_confidence_v27_7 import (
    PredictionError,
    PredictionInput,
    PredictionPolicy,
    create_binding,
    export_csv,
    generate_batch,
    generate_prediction,
    load_history,
    save_history,
    verify_binding,
    verify_history,
    verify_record,
)


def check(name, condition):
    print(f"{name:<78}: {condition}")
    if not condition:
        raise AssertionError(name)


def blocked(fn):
    try:
        fn()
    except PredictionError:
        return True
    return False


binding = create_binding(
    model_version="27.6",
    model_hash="a" * 64,
    feature_names=("rsi", "macd", "atr"),
    classes=(-1, 0, 1),
)

policy = PredictionPolicy(
    min_confidence=Decimal("0.55"),
    min_margin=Decimal("0.10"),
    max_entropy=Decimal("0.85"),
    force_hold_on_low_confidence=True,
    hold_label=0,
)

strong_buy = generate_prediction(
    PredictionInput("P1", "2026-07-28T20:00:00-07:00", (60, 1.2, 2.5)),
    binding=binding,
    probabilities=(Decimal("0.05"), Decimal("0.10"), Decimal("0.85")),
    policy=policy,
)

uncertain = generate_prediction(
    PredictionInput("P2", "2026-07-28T20:01:00-07:00", (50, 0.1, 2.0)),
    binding=binding,
    probabilities=(Decimal("0.32"), Decimal("0.35"), Decimal("0.33")),
    policy=policy,
)

check("V27.7 engine version verified", m.VERSION == "27.7")
check("Model binding created", binding.model_version == "27.6")
check("Binding hash verified", verify_binding(binding))
check("BUY raw prediction generated", strong_buy.raw_label == 1)
check("BUY final prediction retained", strong_buy.final_label == 1)
check("Confidence calculated", strong_buy.confidence == Decimal("0.850000"))
check("Probability margin calculated", strong_buy.probability_margin == Decimal("0.750000"))
check("Entropy calculated", Decimal("0") <= strong_buy.normalized_entropy <= Decimal("1"))
check("High-confidence prediction not overridden", not strong_buy.forced_hold)
check("Low-confidence raw prediction generated", uncertain.raw_label == 0)
check("Low-confidence HOLD enforced", uncertain.final_label == 0 and uncertain.forced_hold)
check("Low-confidence reasons recorded", {
    "LOW_CONFIDENCE", "LOW_MARGIN", "HIGH_ENTROPY"
}.issubset(set(uncertain.reason_codes)))
check("Prediction hash verified", verify_record(strong_buy))
check("Deterministic prediction returned", strong_buy == generate_prediction(
    PredictionInput("P1", "2026-07-28T20:00:00-07:00", (60, 1.2, 2.5)),
    binding=binding,
    probabilities=(Decimal("0.05"), Decimal("0.10"), Decimal("0.85")),
    policy=policy,
))

history = generate_batch(
    (
        PredictionInput("P1", "2026-07-28T20:00:00-07:00", (60, 1.2, 2.5)),
        PredictionInput("P2", "2026-07-28T20:01:00-07:00", (50, 0.1, 2.0)),
        PredictionInput("P3", "2026-07-28T20:02:00-07:00", (35, -1.0, 3.0)),
    ),
    binding=binding,
    probability_rows=(
        (Decimal("0.05"), Decimal("0.10"), Decimal("0.85")),
        (Decimal("0.32"), Decimal("0.35"), Decimal("0.33")),
        (Decimal("0.80"), Decimal("0.15"), Decimal("0.05")),
    ),
    policy=policy,
)

check("Batch prediction created", len(history.records) == 3)
check("SELL prediction generated", history.records[2].final_label == -1)
check("History hash verified", verify_history(history))

no_override = generate_prediction(
    PredictionInput("P4", "2026-07-28T20:03:00-07:00", (50, 0, 2)),
    binding=binding,
    probabilities=(Decimal("0.40"), Decimal("0.30"), Decimal("0.30")),
    policy=replace(policy, force_hold_on_low_confidence=False),
)
check("Override can be disabled", no_override.final_label == -1 and not no_override.forced_hold)

check("Invalid model hash blocked", blocked(lambda: create_binding(
    model_version="27.6",
    model_hash="BAD",
    feature_names=("a",),
    classes=(-1, 0, 1),
)))
check("Duplicate feature schema blocked", blocked(lambda: create_binding(
    model_version="27.6",
    model_hash="b" * 64,
    feature_names=("a", "a"),
    classes=(-1, 0, 1),
)))
check("Feature-width mismatch blocked", blocked(lambda: generate_prediction(
    PredictionInput("BAD", "2026-07-28T20:00:00-07:00", (1, 2)),
    binding=binding,
    probabilities=(Decimal("0.2"), Decimal("0.3"), Decimal("0.5")),
    policy=policy,
)))
check("Probability count mismatch blocked", blocked(lambda: generate_prediction(
    PredictionInput("BAD", "2026-07-28T20:00:00-07:00", (1, 2, 3)),
    binding=binding,
    probabilities=(Decimal("0.5"), Decimal("0.5")),
    policy=policy,
)))
check("Invalid probability sum blocked", blocked(lambda: generate_prediction(
    PredictionInput("BAD", "2026-07-28T20:00:00-07:00", (1, 2, 3)),
    binding=binding,
    probabilities=(Decimal("0.4"), Decimal("0.4"), Decimal("0.4")),
    policy=policy,
)))
check("Missing HOLD class blocked", blocked(lambda: generate_prediction(
    PredictionInput("BAD", "2026-07-28T20:00:00-07:00", (1, 2, 3)),
    binding=create_binding(
        model_version="27.6",
        model_hash="c" * 64,
        feature_names=("a", "b", "c"),
        classes=(-1, 1),
    ),
    probabilities=(Decimal("0.5"), Decimal("0.5")),
    policy=policy,
)))
check("Duplicate batch ID blocked", blocked(lambda: generate_batch(
    (
        PredictionInput("DUP", "T1", (1, 2, 3)),
        PredictionInput("DUP", "T2", (1, 2, 3)),
    ),
    binding=binding,
    probability_rows=((0.2, 0.3, 0.5), (0.2, 0.3, 0.5)),
    policy=policy,
)))

tampered_record = replace(strong_buy, confidence=Decimal("0.999999"))
check("Tampered prediction detected", blocked(lambda: verify_record(tampered_record)))

tampered_history = replace(history, history_hash="BROKEN")
check("Tampered history detected", blocked(lambda: verify_history(tampered_history)))

with tempfile.TemporaryDirectory() as folder:
    folder = Path(folder)
    json_path = folder / "history.json"
    csv_path = folder / "history.csv"

    save_history(history, json_path)
    loaded = load_history(json_path)
    check("History save and load passed", loaded == history)

    export_csv(history, csv_path)
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    check("CSV export passed", len(rows) == 3)

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    payload["records"][0]["final_label"] = 0
    json_path.write_text(json.dumps(payload), encoding="utf-8")
    check("Tampered saved history blocked", blocked(lambda: load_history(json_path)))

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

print("=" * 98)
print("V27.7 offline prediction and confidence test completed successfully.")
print("Probabilities, confidence, margin, entropy, HOLD override, model binding,")
print("batch history, JSON/CSV persistence, hashing, and tamper checks passed.")
print("Market/account/network/broker/order/live execution remained blocked.")
