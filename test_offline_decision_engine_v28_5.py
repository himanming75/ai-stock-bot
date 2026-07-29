from dataclasses import replace
from decimal import Decimal
from pathlib import Path
import ast
import json
import tempfile

import backtest.offline_decision_engine_v28_5 as m
from backtest.offline_decision_engine_v28_5 import (
    DecisionError,
    DecisionInput,
    DecisionPolicy,
    create_history,
    load_history,
    make_decision,
    save_history,
    verify_history,
    verify_record,
)


def check(name, condition):
    print(f"{name:<88}: {condition}")
    if not condition:
        raise AssertionError(name)


def blocked(fn):
    try:
        fn()
    except DecisionError:
        return True
    return False


policy = DecisionPolicy(
    hold_label=0,
    min_confidence=Decimal("0.55"),
    min_agreement=Decimal("0.60"),
    max_entropy=Decimal("0.85"),
    max_risk_score=Decimal("0.65"),
    max_position_fraction=Decimal("0.10"),
    min_position_fraction=Decimal("0.01"),
)

buy = make_decision(
    DecisionInput(
        decision_id="D-BUY",
        timestamp="2026-07-28T22:45:00-07:00",
        symbol="AAPL",
        ensemble_label=1,
        confidence=Decimal("0.82"),
        agreement=Decimal("0.75"),
        entropy=Decimal("0.42"),
        risk_score=Decimal("0.30"),
        expected_return_pct=Decimal("4.5"),
        model_hash="a" * 64,
        ensemble_hash="b" * 64,
    ),
    policy,
)

sell = make_decision(
    DecisionInput(
        decision_id="D-SELL",
        timestamp="2026-07-28T22:46:00-07:00",
        symbol="MSFT",
        ensemble_label=-1,
        confidence=Decimal("0.78"),
        agreement=Decimal("0.70"),
        entropy=Decimal("0.50"),
        risk_score=Decimal("0.35"),
        expected_return_pct=Decimal("3.0"),
        model_hash="c" * 64,
        ensemble_hash="d" * 64,
    ),
    policy,
)

low_confidence = make_decision(
    DecisionInput(
        decision_id="D-LOW",
        timestamp="2026-07-28T22:47:00-07:00",
        symbol="NVDA",
        ensemble_label=1,
        confidence=Decimal("0.40"),
        agreement=Decimal("0.72"),
        entropy=Decimal("0.40"),
        risk_score=Decimal("0.20"),
        expected_return_pct=Decimal("5.0"),
        model_hash="e" * 64,
        ensemble_hash="f" * 64,
    ),
    policy,
)

high_risk = make_decision(
    DecisionInput(
        decision_id="D-RISK",
        timestamp="2026-07-28T22:48:00-07:00",
        symbol="TSLA",
        ensemble_label=1,
        confidence=Decimal("0.80"),
        agreement=Decimal("0.80"),
        entropy=Decimal("0.35"),
        risk_score=Decimal("0.90"),
        expected_return_pct=Decimal("8.0"),
        model_hash="1" * 64,
        ensemble_hash="2" * 64,
    ),
    policy,
)

check("V28.5 engine version verified", m.VERSION == "28.5")
check("BUY decision created", buy.final_label == 1)
check("SELL decision created", sell.final_label == -1)
check("BUY position size calculated", buy.recommended_position_fraction > Decimal("0"))
check("SELL position size calculated", sell.recommended_position_fraction > Decimal("0"))
check("Position size stayed within maximum", buy.recommended_position_fraction <= Decimal("0.10"))
check("Low confidence forced HOLD", low_confidence.final_label == 0 and low_confidence.forced_hold)
check("Low confidence reason recorded", "LOW_CONFIDENCE" in low_confidence.reason_codes)
check("High risk forced HOLD", high_risk.final_label == 0 and high_risk.forced_hold)
check("Risk reason recorded", "RISK_LIMIT_EXCEEDED" in high_risk.reason_codes)
check("HOLD position size is zero", high_risk.recommended_position_fraction == Decimal("0"))
check("Decision hash verified", verify_record(buy))
check("Deterministic decision returned", buy == make_decision(
    DecisionInput(
        decision_id="D-BUY",
        timestamp="2026-07-28T22:45:00-07:00",
        symbol="AAPL",
        ensemble_label=1,
        confidence=Decimal("0.82"),
        agreement=Decimal("0.75"),
        entropy=Decimal("0.42"),
        risk_score=Decimal("0.30"),
        expected_return_pct=Decimal("4.5"),
        model_hash="a" * 64,
        ensemble_hash="b" * 64,
    ),
    policy,
))

no_override = make_decision(
    DecisionInput(
        decision_id="D-NO-OVERRIDE",
        timestamp="2026-07-28T22:49:00-07:00",
        symbol="META",
        ensemble_label=1,
        confidence=Decimal("0.30"),
        agreement=Decimal("0.30"),
        entropy=Decimal("0.95"),
        risk_score=Decimal("0.90"),
        expected_return_pct=Decimal("2.0"),
        model_hash="3" * 64,
        ensemble_hash="4" * 64,
    ),
    replace(policy, force_hold_on_rule_failure=False),
)
check("HOLD override can be disabled", no_override.final_label == 1 and not no_override.forced_hold)

negative_return = make_decision(
    DecisionInput(
        decision_id="D-NEGATIVE",
        timestamp="2026-07-28T22:50:00-07:00",
        symbol="AMD",
        ensemble_label=1,
        confidence=Decimal("0.80"),
        agreement=Decimal("0.80"),
        entropy=Decimal("0.30"),
        risk_score=Decimal("0.20"),
        expected_return_pct=Decimal("-1.0"),
        model_hash="5" * 64,
        ensemble_hash="6" * 64,
    ),
    policy,
)
check("Non-positive expected return forced HOLD", negative_return.final_label == 0)
check("Expected return reason recorded", "NON_POSITIVE_EXPECTED_RETURN" in negative_return.reason_codes)

history = create_history((buy, sell, low_confidence, high_risk))
check("Decision history created", len(history.decisions) == 4)
check("History hash verified", verify_history(history))

check("Invalid confidence blocked", blocked(lambda: make_decision(
    replace(
        DecisionInput(
            "BAD", "T", "AAPL", 1, Decimal("0.5"), Decimal("0.5"),
            Decimal("0.5"), Decimal("0.5"), Decimal("1"),
            "7" * 64, "8" * 64,
        ),
        confidence=Decimal("1.5"),
    ),
    policy,
)))
check("Invalid risk score blocked", blocked(lambda: make_decision(
    DecisionInput(
        "BAD", "T", "AAPL", 1, Decimal("0.5"), Decimal("0.5"),
        Decimal("0.5"), Decimal("-0.1"), Decimal("1"),
        "7" * 64, "8" * 64,
    ),
    policy,
)))
check("Invalid model hash blocked", blocked(lambda: make_decision(
    DecisionInput(
        "BAD", "T", "AAPL", 1, Decimal("0.5"), Decimal("0.5"),
        Decimal("0.5"), Decimal("0.5"), Decimal("1"),
        "BAD", "8" * 64,
    ),
    policy,
)))
check("Invalid position policy blocked", blocked(lambda: DecisionPolicy(
    max_position_fraction=Decimal("0.01"),
    min_position_fraction=Decimal("0.10"),
)))
check("Duplicate decision ID blocked", blocked(lambda: create_history((buy, buy))))

tampered_record = replace(buy, recommended_position_fraction=Decimal("0.50"))
check("Tampered decision detected", blocked(lambda: verify_record(tampered_record)))

tampered_history = replace(history, history_hash="BROKEN")
check("Tampered history detected", blocked(lambda: verify_history(tampered_history)))

with tempfile.TemporaryDirectory() as folder:
    path = Path(folder) / "decisions.json"
    save_history(history, path)
    loaded = load_history(path)
    check("History save and load passed", loaded == history)

    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["decisions"][0]["final_label"] = 0
    path.write_text(json.dumps(payload), encoding="utf-8")
    check("Tampered saved history blocked", blocked(lambda: load_history(path)))

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

print("=" * 108)
print("V28.5 offline decision engine test completed successfully.")
print("BUY/HOLD/SELL decisions, confidence, agreement, entropy, risk rules,")
print("position sizing, history, persistence, hashing, and tamper checks passed.")
print("Market/account/network/broker/order/live execution remained blocked.")
