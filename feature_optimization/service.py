from __future__ import annotations
from decimal import Decimal
import json
from pathlib import Path
from typing import Any

from .dataset import DatasetBuilder
from .ensemble import EnsembleScorer
from .features import FactorEngine, TechnicalFeatureEngine
from .optimization import (
    AutoOptimizer,
    ChampionCandidatePreview,
    OptimizationHistory,
    RollbackPreview,
)
from .processing import CorrelationFilter, FeatureNormalizer, FeatureSelector


def fixture_bars(start: Decimal, step: Decimal) -> list[dict[str, Any]]:
    rows = []
    price = start
    for index in range(30):
        close = price + step
        rows.append({
            "timestamp": f"2026-03-{index + 1:02d}",
            "open": str(price),
            "high": str(max(price, close) + Decimal("1")),
            "low": str(min(price, close) - Decimal("1")),
            "close": str(close),
            "volume": str(1000000 + index * 25000),
        })
        price = close
    return rows


def run(root: Path) -> dict[str, Any]:
    actual = root / "release/feature_engine_auto_optimization/actual"
    actual.mkdir(parents=True, exist_ok=True)

    plugin_result = json.loads(
        (
            root / "release/multi_broker_strategy_plugins/actual/"
                   "multi_broker_strategy_plugins_result.json"
        ).read_text(encoding="utf-8-sig")
    )

    definitions = [
        ("AAPL", Decimal("180"), Decimal("0.8")),
        ("MSFT", Decimal("390"), Decimal("0.5")),
        ("SPY", Decimal("500"), Decimal("0.2")),
        ("XLV", Decimal("140"), Decimal("0.3")),
    ]

    technical_engine = TechnicalFeatureEngine()
    factor_engine = FactorEngine()
    raw_rows = []
    symbols = []
    labels = []

    for index, (symbol, start, step) in enumerate(definitions):
        technical = technical_engine.build(fixture_bars(start, step))
        factors = factor_engine.build(
            technical=technical,
            sector_score=Decimal("0.75") - Decimal(index) * Decimal("0.05"),
            event_score=Decimal("0.65") - Decimal(index) * Decimal("0.03"),
            regime_score=Decimal("0.80"),
        )
        raw_rows.append(factors)
        symbols.append(symbol)
        labels.append(Decimal("1") if index < 2 else Decimal("0"))

    normalized_rows = FeatureNormalizer().min_max(raw_rows)
    correlations = {
        "trend_factor": {
            "momentum_factor": Decimal("0.92"),
            "quality_factor": Decimal("0.20"),
        },
        "momentum_factor": {
            "trend_factor": Decimal("0.92"),
            "quality_factor": Decimal("0.18"),
        },
        "quality_factor": {
            "trend_factor": Decimal("0.20"),
            "momentum_factor": Decimal("0.18"),
        },
        "liquidity_factor": {},
        "sector_factor": {},
        "event_factor": {},
        "regime_factor": {},
    }
    filtered = CorrelationFilter().select(
        correlations=correlations,
        threshold=Decimal("0.85"),
    )
    importance = {
        "trend_factor": Decimal("0.25"),
        "momentum_factor": Decimal("0.22"),
        "quality_factor": Decimal("0.15"),
        "liquidity_factor": Decimal("0.10"),
        "sector_factor": Decimal("0.12"),
        "event_factor": Decimal("0.08"),
        "regime_factor": Decimal("0.08"),
    }
    selected = FeatureSelector().rank(
        importance=importance,
        selected_features=filtered["selected"],
        maximum_features=5,
    )
    selected_names = [row["feature"] for row in selected]

    dataset = DatasetBuilder().build(
        symbols=symbols,
        feature_rows=normalized_rows,
        labels=labels,
        feature_names=selected_names,
    )
    (actual / "dataset.json").write_text(
        json.dumps(dataset, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    strategy_scores = {
        row["strategy_id"]: Decimal(row["score"])
        for row in plugin_result.get("strategy_evaluations", [])
    }
    weights = {
        strategy_id: Decimal("1")
        for strategy_id in strategy_scores
    }
    ensemble = EnsembleScorer().score(
        strategy_scores=strategy_scores,
        weights=weights,
    )

    optimizer = AutoOptimizer()
    def objective(params):
        threshold = Decimal(str(params["threshold"]))
        weight = Decimal(str(params["weight"]))
        lookback = Decimal(str(params["lookback"]))
        return (
            Decimal("1")
            - abs(threshold - Decimal("0.7")) * Decimal("0.8")
            - abs(weight - Decimal("1.0")) * Decimal("0.2")
            - abs(lookback - Decimal("20")) * Decimal("0.01")
        )

    grid = optimizer.grid_search(
        grid={
            "threshold": [0.6, 0.7, 0.8],
            "weight": [0.8, 1.0, 1.2],
            "lookback": [10, 20, 30],
        },
        objective=objective,
    )
    random_result = optimizer.random_search(
        space={
            "threshold": [0.55, 0.65, 0.75, 0.85],
            "weight": [0.8, 1.0, 1.2],
            "lookback": [10, 15, 20, 25, 30],
        },
        evaluations=15,
        objective=objective,
    )

    history_path = actual / "optimization_history.jsonl"
    if history_path.exists():
        history_path.unlink()
    history = OptimizationHistory(history_path)
    grid_history = history.append(
        strategy_id="ensemble_v1",
        result=grid,
    )
    random_history = history.append(
        strategy_id="ensemble_v1",
        result=random_result,
    )

    champion = ChampionCandidatePreview().evaluate(
        current_score=Decimal("0.78"),
        candidate_score=Decimal(grid["best"]["score"]),
        minimum_margin=Decimal("0.05"),
    )
    rollback = RollbackPreview().build(
        current_version="ensemble_v1.1",
        target_version="ensemble_v1.0",
    )

    checks = {
        "plugin_framework_pass": plugin_result.get("status") == "PASS",
        "four_feature_rows": len(raw_rows) == 4,
        "normalization_complete": len(normalized_rows) == 4,
        "correlation_filter_dropped_one": len(filtered["dropped"]) == 1,
        "five_features_selected": len(selected_names) == 5,
        "dataset_created": dataset["row_count"] == 4,
        "dataset_fingerprint_valid": len(dataset["dataset_fingerprint"]) == 64,
        "ensemble_created": bool(ensemble["ensemble_score"]),
        "grid_27_evaluations": grid["evaluation_count"] == 27,
        "random_15_evaluations": random_result["evaluation_count"] == 15,
        "history_two_records": (
            history_path.read_text(encoding="utf-8-sig").count("\n") == 2
        ),
        "champion_preview_created": champion["operator_approval_required"] is True,
        "rollback_preview_created": rollback["rollback_preview_allowed"] is True,
        "orders_not_created": ensemble["order_created"] is False,
    }

    result = {
        "stage": "FEATURE_ENGINE_AUTO_OPTIMIZATION_FRAMEWORK",
        "state": "OFFLINE_QUALIFIED",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "failed": [k for k, v in checks.items() if not v],
        "technical_feature_engine": "READY",
        "factor_engine": "READY",
        "feature_normalization": "READY",
        "correlation_filter": "READY",
        "feature_selection": "READY",
        "feature_importance": "READY",
        "dataset_builder": "READY",
        "market_regime_feature_set": "READY",
        "ensemble_scoring": "READY",
        "grid_optimization": "READY",
        "random_optimization": "READY",
        "optimization_history": "READY",
        "champion_candidate_preview": "READY",
        "rollback_preview": "READY",
        "selected_features": selected,
        "correlation_filter_result": filtered,
        "dataset_summary": {
            "row_count": dataset["row_count"],
            "feature_count": dataset["feature_count"],
            "dataset_fingerprint": dataset["dataset_fingerprint"],
        },
        "ensemble_result": ensemble,
        "grid_search": grid,
        "random_search": random_result,
        "champion_preview": champion,
        "rollback_preview_result": rollback,
        "actual_model_training_performed": False,
        "actual_strategy_parameters_changed": False,
        "actual_strategy_promotion_performed": False,
        "actual_rollback_performed": False,
        "actual_external_network_used": False,
        "actual_broker_read_performed": False,
        "actual_broker_write_performed": False,
        "actual_order_submission_performed": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
        "next_fixed_development": "SHADOW_TRADING_AND_PRODUCTION_APPROVAL_FRAMEWORK",
    }
    (actual / "feature_engine_auto_optimization_result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result
