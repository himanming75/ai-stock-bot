from __future__ import annotations
from pathlib import Path
from typing import Any

from multi_timeframe_regime.io import load_json, digest_payload
from multi_timeframe_regime.resample import resample_bars
from multi_timeframe_regime.frame_analysis import analyze_frame
from multi_timeframe_regime.consensus import build_consensus
from multi_timeframe_regime.decision import position_multiplier, recommend_strategies
from v89_engine.discovery import discover_historical_files
from v89_engine.io import load_bars

def evaluate(root: Path, explicit_input: str = "") -> dict[str, Any]:
    policy = load_json(
        root / "release/v93_33_to_v93_64/input/multi_timeframe_policy.json"
    )
    base_regime = load_json(
        root / "release/v93_01_to_v93_32/actual/market_regime_result.json"
    )

    discovery = discover_historical_files(root)
    selected = Path(explicit_input) if explicit_input else (
        Path(discovery["selected"]["path"]) if discovery.get("selected") else None
    )

    if not selected or not selected.exists():
        return {
            "stage": "V93.64",
            "stage_range": "V93.33-V93.64",
            "state": "MULTI_TIMEFRAME_HISTORICAL_DATA_REQUIRED",
            "status": "PASS",
            "paper_only": True,
            "broker_write_enabled": False,
            "order_submission_enabled": False,
            "live_trading_enabled": False,
            "external_network_enabled": False,
        }

    bars = load_bars(selected)
    definitions = policy.get("timeframes", {
        "SHORT": 1,
        "MEDIUM": 3,
        "LONG": 5,
    })
    frames = []
    for name, factor in definitions.items():
        sampled = resample_bars(bars, int(factor))
        if len(sampled) < int(policy.get("minimum_bars_per_frame", 30)):
            continue
        frames.append(analyze_frame(sampled, policy, name))

    weights = {
        key: float(value)
        for key, value in policy.get(
            "timeframe_weights",
            {"SHORT": 0.2, "MEDIUM": 0.3, "LONG": 0.5},
        ).items()
    }
    consensus = build_consensus(frames, weights)
    base_recommendations = base_regime.get(
        "recommended_strategies",
        ["MOMENTUM", "EMA_CROSS", "MACD", "RSI", "BOLLINGER"],
    )
    recommendations = recommend_strategies(consensus, base_recommendations)
    base_multiplier = float(base_regime.get("effective_position_multiplier", 1.0))
    effective_multiplier = position_multiplier(consensus, base_multiplier)

    checks = {
        "minimum_frame_count": len(frames) >= int(policy.get("minimum_frame_count", 3)),
        "minimum_alignment": float(consensus["alignment_pct"]) >= float(policy.get("minimum_alignment_pct", 66.0)),
        "recommendations_present": bool(recommendations),
        "base_regime_ready": base_regime.get("state") == "MARKET_REGIME_ENGINE_READY",
    }
    failed = [name for name, passed in checks.items() if not passed]
    state = (
        "MULTI_TIMEFRAME_REGIME_READY"
        if not failed
        else "MULTI_TIMEFRAME_REGIME_REVIEW_REQUIRED"
    )

    body = {
        "stage": "V93.64",
        "stage_range": "V93.33-V93.64",
        "state": state,
        "status": "PASS",
        "historical_input": str(selected.resolve()),
        "source_bar_count": len(bars),
        "frame_count": len(frames),
        "frames": frames,
        "consensus": consensus,
        "base_recommendations": base_recommendations,
        "recommended_strategies": recommendations,
        "base_position_multiplier": base_multiplier,
        "effective_position_multiplier": effective_multiplier,
        "checks": checks,
        "failed_checks": failed,
        "policy": policy,
        "paper_only": True,
        "broker_write_enabled": False,
        "order_submission_enabled": False,
        "live_trading_enabled": False,
        "external_network_enabled": False,
        "next_phase": "V94_01_META_STRATEGY_ENGINE",
    }
    body["multi_timeframe_certificate_sha256"] = digest_payload(body)
    return body
