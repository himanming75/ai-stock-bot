from __future__ import annotations
import json
from pathlib import Path
from typing import Any

from .brokers import BrokerRegistry, MockBrokerAdapter
from .strategies import StrategyRegistry
from .versioning import StrategyHotSwapPreview, StrategyVersionManager


def run(root: Path) -> dict[str, Any]:
    actual = root / "release/multi_broker_strategy_plugins/actual"
    actual.mkdir(parents=True, exist_ok=True)

    broker_registry = BrokerRegistry()
    broker_capabilities = broker_registry.list_capabilities()

    mock = broker_registry.get("mock")
    mock_account = mock.preview_account() if isinstance(mock, MockBrokerAdapter) else {}

    strategy_registry = StrategyRegistry()
    strategy_metadata = strategy_registry.list_metadata()
    evaluations = strategy_registry.evaluate_all({
        "momentum": "0.05",
        "z_score": "-1.8",
        "breakout": True,
        "relative_volume": "1.5",
        "spread_bps": "4",
        "trend_strength": "0.75",
    })

    version_preview = StrategyVersionManager().compare(
        current={
            "strategy_id": "momentum_v3",
            "version": "2.9.0",
        },
        candidate={
            "strategy_id": "momentum_v3",
            "version": "3.0.0",
        },
    )
    hot_swap = StrategyHotSwapPreview().preview(
        current_strategy="momentum_v3",
        target_strategy="swing_v1",
        open_positions=0,
        open_orders=0,
    )

    broker_blocks = []
    for broker_id in ("alpaca", "etrade", "ibkr", "schwab", "tradier", "mock"):
        adapter = broker_registry.get(broker_id)
        try:
            adapter.connect()
            broker_blocks.append(False)
        except RuntimeError:
            broker_blocks.append(True)

    checks = {
        "six_brokers_registered": len(broker_capabilities) == 6,
        "mock_account_ready": mock_account.get("status") == "ACTIVE_FIXTURE",
        "five_strategies_registered": len(strategy_metadata) == 5,
        "five_strategy_evaluations": len(evaluations) == 5,
        "all_signals_preview_only": all(
            row["order_created"] is False for row in evaluations
        ),
        "all_broker_connects_blocked": all(broker_blocks),
        "version_upgrade_preview_ready": (
            version_preview["upgrade_preview_allowed"] is True
        ),
        "hot_swap_preview_ready": (
            hot_swap["hot_swap_preview_allowed"] is True
        ),
        "hot_swap_not_performed": (
            hot_swap["actual_hot_swap_performed"] is False
        ),
    }

    result = {
        "stage": "MULTI_BROKER_STRATEGY_PLUGIN_FRAMEWORK",
        "state": "OFFLINE_QUALIFIED",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "failed": [k for k, v in checks.items() if not v],
        "broker_capabilities": broker_capabilities,
        "mock_account_fixture": mock_account,
        "strategy_plugins": strategy_metadata,
        "strategy_evaluations": evaluations,
        "strategy_version_preview": version_preview,
        "strategy_hot_swap_preview": hot_swap,
        "common_broker_interface": "READY",
        "alpaca_adapter": "READY_INTERFACE_ONLY",
        "etrade_adapter": "SKELETON_ONLY",
        "ibkr_adapter": "SKELETON_ONLY",
        "schwab_adapter": "SKELETON_ONLY",
        "tradier_adapter": "SKELETON_ONLY",
        "mock_broker_adapter": "READY_OFFLINE",
        "broker_capability_detection": "READY",
        "strategy_plugin_interface": "READY",
        "plugin_registry": "READY",
        "strategy_version_manager": "READY",
        "strategy_hot_swap": "READY_PREVIEW_ONLY",
        "actual_external_network_used": False,
        "actual_broker_read_performed": False,
        "actual_broker_write_performed": False,
        "actual_strategy_activation_performed": False,
        "actual_hot_swap_performed": False,
        "actual_order_submission_performed": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
        "next_fixed_development": "FEATURE_ENGINE_AND_AUTO_OPTIMIZATION_FRAMEWORK",
    }
    (actual / "multi_broker_strategy_plugins_result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result
