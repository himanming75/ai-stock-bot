from __future__ import annotations
from decimal import Decimal
import json
from pathlib import Path
from typing import Any

from .attribution import PerformanceAttribution
from .champion import ChampionChallengerManager
from .dashboard3 import Dashboard3Builder
from .drift import DriftDetector
from .feature_store import FeatureStore
from .model_registry import ModelRegistry
from .monte_carlo import MonteCarloSimulator
from .optimizer import (
    BayesianOptimizationInterface,
    ParameterOptimizer,
)
from .rebalancer import PortfolioRebalancer
from .upgrade import UpgradeRollbackManager
from .walk_forward import WalkForwardValidator


def run_ai_v2_final(root: Path) -> dict[str, Any]:
    actual = root / "release/ai_v2_final/actual"
    actual.mkdir(parents=True, exist_ok=True)

    bundle1 = json.loads(
        (
            root / "release/ai_v2_mega_bundle_1/actual/"
                   "ai_v2_mega_bundle_1_result.json"
        ).read_text(encoding="utf-8-sig")
    )
    bundle2 = json.loads(
        (
            root / "release/ai_v2_mega_bundle_2/actual/"
                   "ai_v2_mega_bundle_2_result.json"
        ).read_text(encoding="utf-8-sig")
    )

    returns = [
        Decimal("0.01"), Decimal("-0.004"), Decimal("0.006"),
        Decimal("0.003"), Decimal("-0.002"), Decimal("0.009"),
        Decimal("0.004"), Decimal("-0.003"), Decimal("0.007"),
        Decimal("0.005"), Decimal("-0.001"), Decimal("0.008"),
        Decimal("0.002"), Decimal("-0.002"), Decimal("0.006"),
        Decimal("0.004"), Decimal("0.003"), Decimal("-0.003"),
        Decimal("0.005"), Decimal("0.007"), Decimal("-0.002"),
        Decimal("0.004"), Decimal("0.006"), Decimal("-0.001"),
    ]

    walk_forward = WalkForwardValidator().validate(
        returns=returns,
        train_size=8,
        test_size=4,
    )
    monte_carlo = MonteCarloSimulator().simulate(
        returns=returns,
        simulations=1000,
        horizon=60,
    )

    optimizer = ParameterOptimizer()
    def objective(params):
        fast = Decimal(str(params["fast"]))
        slow = Decimal(str(params["slow"]))
        threshold = Decimal(str(params["threshold"]))
        return (
            Decimal("1")
            - abs(fast - Decimal("5")) * Decimal("0.03")
            - abs(slow - Decimal("20")) * Decimal("0.01")
            - abs(threshold - Decimal("0.6")) * Decimal("0.4")
        )

    grid = optimizer.grid_search(
        grid={
            "fast": [3, 5, 8],
            "slow": [15, 20, 30],
            "threshold": [0.5, 0.6, 0.7],
        },
        objective=objective,
    )
    random_result = optimizer.random_search(
        space={
            "fast": [3, 5, 8, 10],
            "slow": [15, 20, 25, 30],
            "threshold": [0.5, 0.6, 0.7, 0.8],
        },
        evaluations=12,
        objective=objective,
    )
    bayesian = BayesianOptimizationInterface().describe()

    champion = ChampionChallengerManager().evaluate(
        candidates=[
            {"strategy_id": "momentum_v2", "score": "0.78"},
            {"strategy_id": "mean_reversion_v2", "score": "0.66"},
            {"strategy_id": "breakout_v2", "score": "0.59"},
        ],
        minimum_score=Decimal("0.70"),
        minimum_margin=Decimal("0.05"),
    )

    feature_store = FeatureStore(actual / "feature_store")
    feature_record = feature_store.register(
        feature_set_name="core_market_features",
        schema_version=1,
        features=[
            "sma_5", "sma_20", "rsi_14", "atr_14",
            "relative_volume", "regime_score", "event_score",
        ],
        metadata={"source": "OFFLINE_FIXTURE_AND_HISTORICAL_ADAPTER"},
    )

    registry = ModelRegistry(actual / "model_registry")
    model_record = registry.register_metadata(
        model_name="strategy_ranker",
        model_version="0.1.0",
        algorithm="DETERMINISTIC_WEIGHTED_SCORE",
        feature_fingerprint=feature_record["fingerprint"],
        metrics={
            "walk_forward_positive_ratio": walk_forward[
                "positive_window_ratio"
            ],
            "monte_carlo_risk_of_ruin": monte_carlo["risk_of_ruin"],
        },
    )
    rollback = registry.rollback_preview(
        current_version="0.1.0",
        target_version="0.0.9",
    )

    drift = DriftDetector().compare(
        baseline={
            "rsi_14_mean": Decimal("55"),
            "atr_14_mean": Decimal("2.5"),
            "event_score_mean": Decimal("0.55"),
        },
        current={
            "rsi_14_mean": Decimal("60"),
            "atr_14_mean": Decimal("2.8"),
            "event_score_mean": Decimal("0.58"),
        },
        warning_threshold=Decimal("0.15"),
        critical_threshold=Decimal("0.35"),
    )

    attribution = PerformanceAttribution().calculate(records=[
        {
            "symbol": "AAPL", "sector": "Technology",
            "strategy_id": "momentum_v2", "pnl": "4.00",
        },
        {
            "symbol": "MSFT", "sector": "Technology",
            "strategy_id": "momentum_v2", "pnl": "-1.00",
        },
        {
            "symbol": "SPY", "sector": "Financials",
            "strategy_id": "mean_reversion_v2", "pnl": "2.00",
        },
        {
            "symbol": "XLV", "sector": "Healthcare",
            "strategy_id": "mean_reversion_v2", "pnl": "1.00",
        },
    ])

    rebalance = PortfolioRebalancer().preview(
        current_weights={
            "AAPL": Decimal("0.25"),
            "MSFT": Decimal("0.30"),
            "SPY": Decimal("0.20"),
            "CASH": Decimal("0.25"),
        },
        target_weights={
            "AAPL": Decimal("0.30"),
            "MSFT": Decimal("0.24"),
            "SPY": Decimal("0.26"),
            "CASH": Decimal("0.20"),
        },
        portfolio_value=Decimal("1000"),
        minimum_trade_notional=Decimal("10"),
    )

    upgrade = UpgradeRollbackManager().build_manifest(
        root=root,
        include_roots=[
            "ai_v2",
            "ai_intelligence",
            "ai_research_final",
        ],
    )

    dashboard = Dashboard3Builder().build(
        walk_forward=walk_forward,
        monte_carlo=monte_carlo,
        optimization={
            "grid_search": grid,
            "random_search": random_result,
            "bayesian_interface": bayesian,
        },
        champion_challenger=champion,
        feature_store=feature_record,
        model_registry=model_record,
        rollback_preview=rollback,
        drift_detection=drift,
        performance_attribution=attribution,
        rebalance_preview=rebalance,
        intelligence_bundle_2_summary={
            "market_regime": bundle2.get("market_regime"),
            "scanner_ranking": bundle2.get("scanner_ranking", [])[:5],
        },
    )
    (actual / "dashboard_v3_data.json").write_text(
        json.dumps(dashboard, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (actual / "upgrade_rollback_manifest.json").write_text(
        json.dumps(upgrade, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    checks = {
        "bundle_1_pass": bundle1.get("status") == "PASS",
        "bundle_2_pass": bundle2.get("status") == "PASS",
        "walk_forward_created": walk_forward["window_count"] > 0,
        "monte_carlo_1000": monte_carlo["simulation_count"] == 1000,
        "grid_search_created": grid["evaluation_count"] == 27,
        "random_search_created": random_result["evaluation_count"] == 12,
        "bayesian_interface_ready": bayesian["interface_ready"] is True,
        "champion_candidate_created": bool(
            champion.get("champion_candidate")
        ),
        "feature_store_registered": len(
            feature_record["fingerprint"]
        ) == 64,
        "model_registry_registered": len(
            model_record["model_fingerprint"]
        ) == 64,
        "drift_detection_created": bool(drift.get("features")),
        "attribution_created": attribution["total_pnl"] == "6.00",
        "rebalance_preview_created": len(
            rebalance["rebalance_preview"]
        ) == 4,
        "dashboard_v3_created": dashboard["schema_version"] == 3,
        "dashboard_read_only": dashboard["read_only"] is True,
        "upgrade_manifest_created": len(
            upgrade["manifest_sha256"]
        ) == 64,
        "actual_training_not_performed": (
            model_record["actual_model_training_performed"] is False
        ),
        "actual_promotion_not_performed": (
            champion["actual_promotion_performed"] is False
        ),
        "actual_rebalance_not_performed": (
            rebalance["actual_portfolio_modified"] is False
        ),
        "broker_actions_unavailable": (
            dashboard["broker_actions_available"] is False
        ),
        "submission_off": (
            dashboard["automatic_order_submission_enabled"] is False
        ),
    }

    production_candidate_ready = all(checks.values())
    result = {
        "stage": "AI_V2_FINAL_MEGA_BUNDLE",
        "state": "AI_V2_FINAL_OFFLINE_QUALIFIED",
        "status": "PASS" if production_candidate_ready else "FAIL",
        "checks": checks,
        "failed": [k for k, v in checks.items() if not v],
        "walk_forward_validation": walk_forward,
        "monte_carlo_simulation": monte_carlo,
        "parameter_optimization": {
            "grid_search": grid,
            "random_search": random_result,
            "bayesian_interface": bayesian,
        },
        "champion_challenger": champion,
        "feature_store": feature_record,
        "model_registry": model_record,
        "rollback_preview": rollback,
        "drift_detection": drift,
        "performance_attribution": attribution,
        "portfolio_rebalance_preview": rebalance,
        "dashboard_v3": dashboard,
        "upgrade_rollback_manifest": upgrade,
        "ai_v2_release_candidate_ready": production_candidate_ready,
        "actual_machine_learning_training_performed": False,
        "actual_bayesian_optimization_performed": False,
        "actual_strategy_promotion_performed": False,
        "actual_model_activation_performed": False,
        "actual_portfolio_modified": False,
        "actual_orders_created": False,
        "actual_market_network_used": False,
        "actual_news_api_used": False,
        "actual_llm_api_used": False,
        "actual_broker_network_used": False,
        "actual_broker_write_used": False,
        "automatic_order_submission_enabled": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
        "remaining_required_work": [
            "P2_TO_P5_ACTUAL_PAPER_VALIDATION",
            "LIVE_VALIDATION_L2_TO_L6",
            "EXTERNAL_DATA_API_INTEGRATION_IF_DESIRED",
            "ACTUAL_MODEL_TRAINING_AFTER_SUFFICIENT_DATA",
        ],
    }
    (actual / "ai_v2_final_result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (actual / "ai_v2_final_certificate.json").write_text(
        json.dumps({
            "certificate_stage": "AI_V2_FINAL_OFFLINE",
            "eligible": production_candidate_ready,
            "status": "PASS" if production_candidate_ready else "FAIL",
            "actual_live_release_allowed": False,
            "paper_validation_required": True,
            "live_validation_required": True,
        }, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result
