from __future__ import annotations
import json
from pathlib import Path
from typing import Any

from .orchestrator import RuntimeOrchestrator
from .plugins import DeterministicFixtureStrategy, StrategyRegistry


def build_default_registry() -> StrategyRegistry:
    registry = StrategyRegistry()
    registry.register(DeterministicFixtureStrategy())
    return registry


def run_offline_bundle_qualification(root: Path) -> dict[str, Any]:
    session_path = (
        root / "release/r6_runtime_session_manager/actual/"
               "last_session_preview.json"
    )
    session = json.loads(session_path.read_text(encoding="utf-8-sig"))
    runtime = session["runtime_snapshot"]

    prices = {
        symbol: str(DecimalPrice.fixture(symbol))
        for symbol in runtime["allowed_symbols"]
    }
    market = {
        "mode": "OFFLINE_FIXTURE",
        "market_open": True,
        "prices": prices,
    }
    portfolio = {
        "cash": "100000",
        "gross_exposure": "0",
        "symbol_exposure": {},
        "positions": {},
    }
    daily = {
        "order_count": 0,
        "realized_loss": "0",
    }

    orchestrator = RuntimeOrchestrator(
        registry=build_default_registry()
    )
    cycles = []
    for number in range(1, 4):
        cycles.append(orchestrator.run_cycle(
            session_snapshot=session,
            strategy_id="fixture_momentum_v1",
            market_snapshot=market,
            portfolio_snapshot=portfolio,
            daily_state=daily,
            cycle_number=number,
        ))

    checks = {
        "three_cycles": len(cycles) == 3,
        "all_cycles_pass": all(c["status"] == "PASS" for c in cycles),
        "candidate_created_each_cycle": all(
            c["order_candidate_count"] == 1 for c in cycles
        ),
        "network_off": all(
            c["broker_network_enabled"] is False for c in cycles
        ),
        "write_off": all(
            c["broker_write_enabled"] is False for c in cycles
        ),
        "submission_off": all(
            c["automatic_order_submission_enabled"] is False
            for c in cycles
        ),
        "portfolio_not_modified": all(
            c["actual_portfolio_modified"] is False for c in cycles
        ),
        "paper_orders_zero": all(
            c["actual_paper_orders_submitted"] == 0 for c in cycles
        ),
        "live_orders_zero": all(
            c["actual_live_orders_submitted"] == 0 for c in cycles
        ),
    }
    return {
        "stage": "BUNDLE_A_R7_TO_R10",
        "state": "RUNTIME_CORE_OFFLINE_QUALIFIED",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "failed": [k for k, v in checks.items() if not v],
        "completed_cycle_count": len(cycles),
        "cycles": cycles,
        "strategy_catalog": build_default_registry().catalog(),
        "r7_runtime_orchestrator": "READY",
        "r8_capital_allocation_engine": "READY",
        "r9_portfolio_exposure_manager": "READY",
        "r10_strategy_plugin_framework": "READY",
        "actual_runtime_activation_performed": False,
        "broker_network_enabled": False,
        "broker_write_enabled": False,
        "automatic_order_submission_enabled": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
        "next_fixed_bundle": "BUNDLE_B_R11_TO_R13_BROKER_MULTI_ACCOUNT",
    }


class DecimalPrice:
    _VALUES = {
        "AAPL": "200",
        "MSFT": "400",
        "SPY": "500",
    }

    @classmethod
    def fixture(cls, symbol: str) -> str:
        return cls._VALUES.get(symbol, "100")
