from dataclasses import replace
from decimal import Decimal
from pathlib import Path
import ast
import json
import tempfile

import backtest.offline_risk_manager_v28_6 as m
from backtest.offline_risk_manager_v28_6 import (
    RiskError,
    RiskInput,
    RiskPolicy,
    create_history,
    evaluate_risk,
    load_history,
    save_history,
    verify_history,
    verify_record,
)


def check(name, condition):
    print(f"{name:<90}: {condition}")
    if not condition:
        raise AssertionError(name)


def blocked(fn):
    try:
        fn()
    except RiskError:
        return True
    return False


policy = RiskPolicy()

approved = evaluate_risk(
    RiskInput(
        risk_id="R-APPROVED",
        timestamp="2026-07-28T23:00:00-07:00",
        symbol="AAPL",
        sector="TECHNOLOGY",
        requested_position_fraction=Decimal("0.03"),
        daily_pnl_pct=Decimal("-0.5"),
        weekly_pnl_pct=Decimal("-1.0"),
        current_drawdown_pct=Decimal("3.0"),
        open_position_count=3,
        current_symbol_exposure=Decimal("0.05"),
        current_sector_exposure=Decimal("0.20"),
        portfolio_heat=Decimal("0.02"),
        max_pair_correlation=Decimal("0.60"),
        kelly_fraction=Decimal("0.25"),
        consecutive_losses=1,
        decision_hash="a" * 64,
    ),
    policy,
)

daily_block = evaluate_risk(
    replace(
        RiskInput(
            "R-DAILY", "T", "MSFT", "TECHNOLOGY", Decimal("0.02"),
            Decimal("-2.5"), Decimal("-2.0"), Decimal("5"), 2,
            Decimal("0.03"), Decimal("0.20"), Decimal("0.01"),
            Decimal("0.50"), Decimal("0.10"), 1, "b" * 64,
        )
    ),
    policy,
)

weekly_block = evaluate_risk(
    RiskInput(
        "R-WEEKLY", "T", "META", "TECHNOLOGY", Decimal("0.02"),
        Decimal("-1.0"), Decimal("-6.0"), Decimal("5"), 2,
        Decimal("0.03"), Decimal("0.20"), Decimal("0.01"),
        Decimal("0.50"), Decimal("0.10"), 1, "c" * 64,
    ),
    policy,
)

drawdown_block = evaluate_risk(
    RiskInput(
        "R-DD", "T", "NVDA", "TECHNOLOGY", Decimal("0.02"),
        Decimal("-1.0"), Decimal("-2.0"), Decimal("13"), 2,
        Decimal("0.03"), Decimal("0.20"), Decimal("0.01"),
        Decimal("0.50"), Decimal("0.10"), 1, "d" * 64,
    ),
    policy,
)

position_block = evaluate_risk(
    RiskInput(
        "R-POS", "T", "AMD", "TECHNOLOGY", Decimal("0.02"),
        Decimal("-1.0"), Decimal("-2.0"), Decimal("5"), 10,
        Decimal("0.03"), Decimal("0.20"), Decimal("0.01"),
        Decimal("0.50"), Decimal("0.10"), 1, "e" * 64,
    ),
    policy,
)

exposure_block = evaluate_risk(
    RiskInput(
        "R-EXP", "T", "TSLA", "CONSUMER", Decimal("0.10"),
        Decimal("-1.0"), Decimal("-2.0"), Decimal("5"), 2,
        Decimal("0.10"), Decimal("0.35"), Decimal("0.02"),
        Decimal("0.50"), Decimal("0.10"), 1, "f" * 64,
    ),
    policy,
)

heat_block = evaluate_risk(
    RiskInput(
        "R-HEAT", "T", "NFLX", "COMMUNICATION", Decimal("0.03"),
        Decimal("-1.0"), Decimal("-2.0"), Decimal("5"), 2,
        Decimal("0.02"), Decimal("0.20"), Decimal("0.04"),
        Decimal("0.50"), Decimal("0.10"), 1, "1" * 64,
    ),
    policy,
)

corr_block = evaluate_risk(
    RiskInput(
        "R-CORR", "T", "GOOG", "COMMUNICATION", Decimal("0.02"),
        Decimal("-1.0"), Decimal("-2.0"), Decimal("5"), 2,
        Decimal("0.02"), Decimal("0.20"), Decimal("0.01"),
        Decimal("0.95"), Decimal("0.10"), 1, "2" * 64,
    ),
    policy,
)

circuit = evaluate_risk(
    RiskInput(
        "R-CIRCUIT", "T", "AMZN", "CONSUMER", Decimal("0.02"),
        Decimal("-1.0"), Decimal("-2.0"), Decimal("5"), 2,
        Decimal("0.02"), Decimal("0.20"), Decimal("0.01"),
        Decimal("0.50"), Decimal("0.10"), 4, "3" * 64,
    ),
    policy,
)

emergency = evaluate_risk(
    RiskInput(
        "R-EMERGENCY", "T", "SPY", "ETF", Decimal("0.02"),
        Decimal("-1.0"), Decimal("-2.0"), Decimal("22"), 2,
        Decimal("0.02"), Decimal("0.20"), Decimal("0.01"),
        Decimal("0.50"), Decimal("0.10"), 1, "4" * 64,
    ),
    policy,
)

check("V28.6 engine version verified", m.VERSION == "28.6")
check("Approved trade passed risk checks", approved.approved)
check("Kelly fraction was capped", approved.capped_kelly_fraction == Decimal("0.200000"))
check("Approved size respects Kelly cap", approved.approved_position_fraction <= approved.capped_kelly_fraction)
check("Aggregate risk score calculated", Decimal("0") <= approved.aggregate_risk_score <= Decimal("1"))
check("Daily loss limit enforced", "DAILY_LOSS_LIMIT" in daily_block.reason_codes)
check("Weekly loss limit enforced", "WEEKLY_LOSS_LIMIT" in weekly_block.reason_codes)
check("Maximum drawdown checked", "MAX_DRAWDOWN" in drawdown_block.reason_codes)
check("Maximum position count checked", "MAX_POSITION_COUNT" in position_block.reason_codes)
check("Symbol exposure checked", "SYMBOL_EXPOSURE_LIMIT" in exposure_block.reason_codes)
check("Sector exposure checked", "SECTOR_EXPOSURE_LIMIT" in exposure_block.reason_codes)
check("Portfolio heat checked", "PORTFOLIO_HEAT_LIMIT" in heat_block.reason_codes)
check("Correlation risk checked", "CORRELATION_LIMIT" in corr_block.reason_codes)
check("Circuit breaker triggered", circuit.circuit_breaker)
check("Cooldown timer created", circuit.cooldown_minutes == 30)
check("Emergency stop triggered", emergency.emergency_stop)
check("Blocked trades have zero position", all(
    item.approved_position_fraction == Decimal("0")
    for item in (
        daily_block, weekly_block, drawdown_block, position_block,
        exposure_block, heat_block, corr_block, circuit, emergency,
    )
))
check("Risk hash verified", verify_record(approved))
check("Deterministic result returned", approved == evaluate_risk(
    RiskInput(
        risk_id="R-APPROVED",
        timestamp="2026-07-28T23:00:00-07:00",
        symbol="AAPL",
        sector="TECHNOLOGY",
        requested_position_fraction=Decimal("0.03"),
        daily_pnl_pct=Decimal("-0.5"),
        weekly_pnl_pct=Decimal("-1.0"),
        current_drawdown_pct=Decimal("3.0"),
        open_position_count=3,
        current_symbol_exposure=Decimal("0.05"),
        current_sector_exposure=Decimal("0.20"),
        portfolio_heat=Decimal("0.02"),
        max_pair_correlation=Decimal("0.60"),
        kelly_fraction=Decimal("0.25"),
        consecutive_losses=1,
        decision_hash="a" * 64,
    ),
    policy,
))

history = create_history((approved, daily_block, circuit, emergency))
check("Risk history created", len(history.records) == 4)
check("History hash verified", verify_history(history))

check("Invalid requested size blocked", blocked(lambda: evaluate_risk(
    replace(
        RiskInput(
            "BAD", "T", "AAPL", "TECH", Decimal("0.02"),
            Decimal("0"), Decimal("0"), Decimal("0"), 0,
            Decimal("0"), Decimal("0"), Decimal("0"),
            Decimal("0"), Decimal("0"), 0, "5" * 64,
        ),
        requested_position_fraction=Decimal("1.5"),
    ),
    policy,
)))
check("Invalid correlation blocked", blocked(lambda: evaluate_risk(
    RiskInput(
        "BAD", "T", "AAPL", "TECH", Decimal("0.02"),
        Decimal("0"), Decimal("0"), Decimal("0"), 0,
        Decimal("0"), Decimal("0"), Decimal("0"),
        Decimal("-0.1"), Decimal("0"), 0, "5" * 64,
    ),
    policy,
)))
check("Invalid decision hash blocked", blocked(lambda: evaluate_risk(
    RiskInput(
        "BAD", "T", "AAPL", "TECH", Decimal("0.02"),
        Decimal("0"), Decimal("0"), Decimal("0"), 0,
        Decimal("0"), Decimal("0"), Decimal("0"),
        Decimal("0"), Decimal("0"), 0, "BAD",
    ),
    policy,
)))
check("Invalid emergency threshold blocked", blocked(lambda: RiskPolicy(
    max_drawdown_pct=Decimal("15"),
    emergency_stop_drawdown_pct=Decimal("10"),
)))
check("Duplicate risk ID blocked", blocked(lambda: create_history((approved, approved))))

tampered_record = replace(approved, approved_position_fraction=Decimal("0.99"))
check("Tampered risk record detected", blocked(lambda: verify_record(tampered_record)))

tampered_history = replace(history, history_hash="BROKEN")
check("Tampered history detected", blocked(lambda: verify_history(tampered_history)))

with tempfile.TemporaryDirectory() as folder:
    path = Path(folder) / "risk_history.json"
    save_history(history, path)
    loaded = load_history(path)
    check("History save and load passed", loaded == history)

    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["records"][0]["approved"] = False
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

print("=" * 110)
print("V28.6 offline risk management test completed successfully.")
print("Loss limits, drawdown, position/exposure limits, heat, correlation, Kelly cap,")
print("circuit breaker, cooldown, emergency stop, persistence, hashing, and tamper checks passed.")
print("Market/account/network/broker/order/live execution remained blocked.")
