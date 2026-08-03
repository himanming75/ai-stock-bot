from __future__ import annotations
from pathlib import Path
from typing import Any

from market_regime_engine.io import load_json, digest_payload
from market_regime_engine.indicators import (
    sma,
    annualized_volatility,
    momentum,
    average_true_range_pct,
    trend_slope_pct,
)
from market_regime_engine.classifier import classify_regime
from market_regime_engine.strategy_mapping import (
    recommend_strategies,
    position_multiplier,
)
from v89_engine.discovery import discover_historical_files
from v89_engine.io import load_bars

def evaluate(root: Path, explicit_input: str = "") -> dict[str, Any]:
    policy = load_json(
        root / "release/v93_01_to_v93_32/input/market_regime_policy.json"
    )
    risk = load_json(
        root / "release/v92_33_to_v92_64/actual/enterprise_risk_center_result.json"
    )
    strategy_lab = load_json(
        root / "release/v91_01_to_v91_32/actual/ultimate_strategy_lab_result.json"
    )

    discovery = discover_historical_files(root)
    selected = Path(explicit_input) if explicit_input else (
        Path(discovery["selected"]["path"])
        if discovery.get("selected") else None
    )

    if not selected or not selected.exists():
        return {
            "stage": "V93.32",
            "stage_range": "V93.01-V93.32",
            "state": "MARKET_REGIME_HISTORICAL_DATA_REQUIRED",
            "status": "PASS",
            "paper_only": True,
            "broker_write_enabled": False,
            "order_submission_enabled": False,
            "live_trading_enabled": False,
            "external_network_enabled": False,
        }

    bars = load_bars(selected)
    closes = [float(bar["close"]) for bar in bars]
    short_period = int(policy.get("short_sma_period", 20))
    long_period = int(policy.get("long_sma_period", 50))
    mom_period = int(policy.get("momentum_period", 20))
    slope_period = int(policy.get("trend_slope_period", 30))

    short_sma = sma(closes, short_period)
    long_sma = sma(closes, long_period)
    latest = closes[-1] if closes else 0.0

    features = {
        "latest_close": round(latest, 4),
        "short_sma": round(short_sma, 4) if short_sma is not None else None,
        "long_sma": round(long_sma, 4) if long_sma is not None else None,
        "price_above_short_sma": (
            latest > short_sma if short_sma is not None else False
        ),
        "price_above_long_sma": (
            latest > long_sma if long_sma is not None else False
        ),
        "momentum_pct": round(momentum(closes, mom_period), 4),
        "trend_slope_pct": round(trend_slope_pct(closes, slope_period), 4),
        "annualized_volatility_pct": round(
            annualized_volatility(closes), 4
        ),
        "atr_pct": round(
            average_true_range_pct(
                bars,
                int(policy.get("atr_period", 14)),
            ),
            4,
        ),
    }

    regime = classify_regime(features, policy)
    available = sorted({
        str(row.get("base_strategy"))
        for row in strategy_lab.get("rankings", [])
        if row.get("base_strategy")
    })
    if not available:
        available = ["MOMENTUM", "EMA_CROSS", "MACD", "RSI", "BOLLINGER"]

    recommended = recommend_strategies(regime, available)
    multiplier = position_multiplier(regime)

    risk_approved = risk.get("risk_approved") is True
    effective_multiplier = multiplier if risk_approved else min(multiplier, 0.25)

    checks = {
        "risk_center_approved": risk_approved,
        "historical_data_sufficient": len(bars) >= long_period,
        "regime_confidence_minimum": (
            float(regime["confidence_score"])
            >= float(policy.get("minimum_confidence_score", 50.0))
        ),
        "recommended_strategies_present": bool(recommended),
    }
    failed = [name for name, passed in checks.items() if not passed]
    state = (
        "MARKET_REGIME_ENGINE_READY"
        if not failed
        else "MARKET_REGIME_ENGINE_REVIEW_REQUIRED"
    )

    body = {
        "stage": "V93.32",
        "stage_range": "V93.01-V93.32",
        "state": state,
        "status": "PASS",
        "historical_input": str(selected.resolve()),
        "bar_count": len(bars),
        "features": features,
        "regime": regime,
        "available_strategies": available,
        "recommended_strategies": recommended,
        "base_position_multiplier": multiplier,
        "effective_position_multiplier": effective_multiplier,
        "risk_center_approved": risk_approved,
        "checks": checks,
        "failed_checks": failed,
        "policy": policy,
        "paper_only": True,
        "broker_write_enabled": False,
        "order_submission_enabled": False,
        "live_trading_enabled": False,
        "external_network_enabled": False,
        "next_phase": "V93_33_MULTI_TIMEFRAME_REGIME",
    }
    body["regime_certificate_sha256"] = digest_payload(body)
    return body
