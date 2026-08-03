from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from explainability_engine.engine import build_explainability_report
try:
    from indicator_engine.engine import evaluate_indicators as _indicator_evaluate
    from indicator_engine.io import parse_bars as _indicator_parse
    INDICATOR_ENGINE_LAYOUT = "indicator_engine"
except ModuleNotFoundError:
    from indicator_engine_v2.engine import compute_indicators as _indicator_evaluate
    from indicator_engine_v2.io import parse_input as _indicator_parse
    INDICATOR_ENGINE_LAYOUT = "indicator_engine_v2"

from multi_asset_backtest.engine import run_multi_asset_backtest
from paper_orchestrator.io import load_json, write_json
from portfolio_scoring.engine import evaluate_portfolio
from portfolio_scoring.io import parse_input as parse_portfolio_input
from strategy_engine_v2.engine import evaluate_strategy
from strategy_engine_v2.io import parse_signals
from backtest_v2.engine import run_backtest
from backtest_v2.io import parse_input as parse_backtest_input
from validation_v2.engine import run_validation



def run_indicator(root: Path) -> dict[str, Any]:
    candidates = [
        root / "release/v86_09_to_v86_16/input/ohlcv_sample.json",
        root / "release/v86_09_to_v86_16/input/ohlcv_input.json",
    ]
    input_path = next(
        (path for path in candidates if path.exists()),
        candidates[0],
    )
    payload = load_json(input_path)
    symbol, bars = _indicator_parse(payload)
    raw_result = _indicator_evaluate(symbol, bars)

    if INDICATOR_ENGINE_LAYOUT == "indicator_engine":
        indicator_payload = raw_result
        strategy_signals = raw_result.get("strategy_signals", [])
        indicator_count = raw_result.get("indicator_count", 0)
        ready_state = "INDICATOR_ENGINE_READY"
    else:
        indicator_payload = raw_result.get("indicators", {})
        strategy_signals = raw_result.get(
            "strategy_signal_payload", {}
        ).get("signals", [])
        indicator_count = raw_result.get(
            "available_indicator_count", 0
        )
        ready_state = raw_result.get(
            "state", "INDICATOR_ENGINE_READY"
        )

    if not raw_result or raw_result.get("status") == "BLOCKED":
        raise RuntimeError(
            "indicator engine did not produce a valid result"
        )

    output = (
        root / "release/v86_09_to_v86_16/actual/"
        "indicator_engine_result.json"
    )
    write_json(output, {
        "stage": "V86.16",
        "stage_range": "V86.09-V86.16",
        "state": ready_state,
        "status": "PASS",
        "indicators": indicator_payload,
        "indicator_result": raw_result,
        "indicator_engine_layout": INDICATOR_ENGINE_LAYOUT,
        "paper_only": True,
        "broker_write_enabled": False,
        "order_submission_enabled": False,
        "live_trading_enabled": False,
        "external_network_enabled": False,
    })
    strategy_input = {
        "symbol": symbol,
        "policy": {
            "buy_threshold": 35,
            "sell_threshold": -35,
            "watch_confidence": 45,
        },
        "signals": strategy_signals,
    }
    strategy_input_path = (
        root / "release/v86_01_to_v86_08/input/"
        "strategy_signal_input_from_orchestrator.json"
    )
    write_json(strategy_input_path, strategy_input)
    return {
        "state": ready_state,
        "output_path": str(output),
        "strategy_input_path": str(strategy_input_path),
        "indicator_count": indicator_count,
        "indicator_engine_layout": INDICATOR_ENGINE_LAYOUT,
    }


def run_strategy(root: Path) -> dict[str, Any]:
    input_path = (
        root / "release/v86_01_to_v86_08/input/"
        "strategy_signal_input_from_orchestrator.json"
    )
    payload = load_json(input_path)
    symbol, signals = parse_signals(payload)
    policy = payload.get("policy", {})
    decision = evaluate_strategy(
        symbol,
        signals,
        buy_threshold=float(policy.get("buy_threshold", 35)),
        sell_threshold=float(policy.get("sell_threshold", -35)),
        watch_confidence=float(policy.get("watch_confidence", 45)),
    )
    output = (
        root / "release/v86_01_to_v86_08/actual/"
        "strategy_engine_v2_result.json"
    )
    write_json(output, {
        "stage": "V86.08",
        "stage_range": "V86.01-V86.08",
        "state": "AI_STRATEGY_ENGINE_V2_READY",
        "status": "PASS",
        "decision": decision.to_dict(),
        "paper_only": True,
        "broker_write_enabled": False,
        "order_submission_enabled": False,
        "live_trading_enabled": False,
        "external_network_enabled": False,
    })
    return {
        "state": "AI_STRATEGY_ENGINE_V2_READY",
        "output_path": str(output),
        "decision": decision.decision,
        "confidence": decision.confidence,
    }


def run_portfolio(root: Path) -> dict[str, Any]:
    input_path = (
        root / "release/v86_17_to_v86_24/input/"
        "portfolio_candidates.json"
    )
    payload = load_json(input_path)
    candidates, policy = parse_portfolio_input(payload)
    portfolio = evaluate_portfolio(candidates, policy)
    output = (
        root / "release/v86_17_to_v86_24/actual/"
        "portfolio_scoring_result.json"
    )
    write_json(output, {
        "stage": "V86.24",
        "stage_range": "V86.17-V86.24",
        "state": "PORTFOLIO_SCORING_ENGINE_READY",
        "status": "PASS",
        "portfolio": portfolio,
        "paper_only": True,
        "broker_write_enabled": False,
        "order_submission_enabled": False,
        "live_trading_enabled": False,
        "external_network_enabled": False,
    })
    return {
        "state": "PORTFOLIO_SCORING_ENGINE_READY",
        "output_path": str(output),
        "portfolio_score": portfolio["portfolio_score"],
        "allocation_count": len(portfolio["recommended_allocations"]),
    }


def run_explainability(root: Path) -> dict[str, Any]:
    strategy = load_json(
        root / "release/v86_01_to_v86_08/actual/"
        "strategy_engine_v2_result.json"
    )
    indicators = load_json(
        root / "release/v86_09_to_v86_16/actual/"
        "indicator_engine_result.json"
    )
    portfolio = load_json(
        root / "release/v86_17_to_v86_24/actual/"
        "portfolio_scoring_result.json"
    )
    report = build_explainability_report(
        strategy,
        indicators,
        portfolio,
    )
    output = (
        root / "release/v86_25_to_v86_32/actual/"
        "ai_explainability_result.json"
    )
    write_json(output, {
        "stage": "V86.32",
        "stage_range": "V86.25-V86.32",
        "state": "AI_EXPLAINABILITY_ENGINE_READY",
        "status": "PASS",
        "report": report,
        "paper_only": True,
        "broker_write_enabled": False,
        "order_submission_enabled": False,
        "live_trading_enabled": False,
        "external_network_enabled": False,
    })
    return {
        "state": "AI_EXPLAINABILITY_ENGINE_READY",
        "output_path": str(output),
        "strategy_risk_count": len(
            report["strategy_explanation"]["risk_factors"]
        ),
        "portfolio_risk_count": len(
            report["portfolio_explanation"]["risk_factors"]
        ),
    }


def run_backtest_step(root: Path) -> dict[str, Any]:
    input_path = (
        root / "release/v87_01_to_v87_08/input/backtest_sample.json"
    )
    payload = load_json(input_path)
    symbol, bars, policy = parse_backtest_input(payload)
    result = run_backtest(symbol, bars, policy)
    output = (
        root / "release/v87_01_to_v87_08/actual/backtest_v2_result.json"
    )
    write_json(output, {
        "stage": "V87.08",
        "stage_range": "V87.01-V87.08",
        "state": "BACKTEST_ENGINE_V2_READY",
        "status": "PASS",
        "backtest": result,
        "paper_only": True,
        "broker_write_enabled": False,
        "order_submission_enabled": False,
        "live_trading_enabled": False,
        "external_network_enabled": False,
    })
    return {
        "state": "BACKTEST_ENGINE_V2_READY",
        "output_path": str(output),
        "total_return_pct": result["total_return_pct"],
        "total_trades": result["trade_statistics"]["total_trades"],
    }


def run_validation_step(root: Path) -> dict[str, Any]:
    payload = load_json(
        root / "release/v87_01_to_v87_08/input/backtest_sample.json"
    )
    symbol, bars, backtest_policy = parse_backtest_input(payload)
    policy = load_json(
        root / "release/v87_09_to_v87_16/input/"
        "walk_forward_stress_policy.json"
    )
    policy["backtest_policy"] = {
        **backtest_policy,
        **policy.get("backtest_policy", {}),
    }
    result = run_validation(symbol, bars, policy)
    state = (
        "BACKTEST_ROBUSTNESS_VALIDATED"
        if result["robustness_passed"]
        else "BACKTEST_ROBUSTNESS_REVIEW_REQUIRED"
    )
    output = (
        root / "release/v87_09_to_v87_16/actual/"
        "walk_forward_stress_validation_result.json"
    )
    write_json(output, {
        "stage": "V87.16",
        "stage_range": "V87.09-V87.16",
        "state": state,
        "status": "PASS",
        "validation": result,
        "paper_only": True,
        "broker_write_enabled": False,
        "order_submission_enabled": False,
        "live_trading_enabled": False,
        "external_network_enabled": False,
    })
    return {
        "state": state,
        "output_path": str(output),
        "robustness_passed": result["robustness_passed"],
        "overfit_risk_score": result["overfit"]["overfit_risk_score"],
    }


def run_multi_asset(root: Path) -> dict[str, Any]:
    payload = load_json(
        root / "release/v87_17_to_v87_24/input/"
        "multi_asset_backtest_input.json"
    )
    result = run_multi_asset_backtest(
        payload.get("assets", []),
        payload.get("policy", {}),
    )
    state = (
        "MULTI_ASSET_BACKTEST_CERTIFIED"
        if result["certified"]
        else "MULTI_ASSET_BACKTEST_REVIEW_REQUIRED"
    )
    output = (
        root / "release/v87_17_to_v87_24/actual/"
        "multi_asset_backtest_result.json"
    )
    write_json(output, {
        "stage": "V87.24",
        "stage_range": "V87.17-V87.24",
        "state": state,
        "status": "PASS",
        "multi_asset": result,
        "paper_only": True,
        "broker_write_enabled": False,
        "order_submission_enabled": False,
        "live_trading_enabled": False,
        "external_network_enabled": False,
    })
    return {
        "state": state,
        "output_path": str(output),
        "asset_count": result["asset_count"],
        "portfolio_return_pct": result["portfolio"]["total_return_pct"],
        "excess_return_pct": result["excess_return_pct"],
    }


STEP_FUNCTIONS = {
    "INDICATOR_ENGINE": run_indicator,
    "STRATEGY_ENGINE": run_strategy,
    "PORTFOLIO_SCORING": run_portfolio,
    "EXPLAINABILITY_ENGINE": run_explainability,
    "BACKTEST_ENGINE": run_backtest_step,
    "ROBUSTNESS_VALIDATION": run_validation_step,
    "MULTI_ASSET_BACKTEST": run_multi_asset,
}
