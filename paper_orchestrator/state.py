from __future__ import annotations

from pathlib import Path
from typing import Any

from paper_orchestrator.io import load_json, write_json


STEP_ORDER = [
    "INDICATOR_ENGINE",
    "STRATEGY_ENGINE",
    "PORTFOLIO_SCORING",
    "EXPLAINABILITY_ENGINE",
    "BACKTEST_ENGINE",
    "ROBUSTNESS_VALIDATION",
    "MULTI_ASSET_BACKTEST",
]


def new_state(run_id: str, observed_at: str) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "observed_at": observed_at,
        "state": "PAPER_ORCHESTRATOR_IN_PROGRESS",
        "current_step": "",
        "completed_steps": [],
        "failed_step": "",
        "error": "",
        "safe_mode": False,
        "paper_only": True,
        "broker_write_enabled": False,
        "order_submission_enabled": False,
        "live_trading_enabled": False,
        "external_network_enabled": False,
    }


def load_or_new(path: Path, run_id: str, observed_at: str) -> dict[str, Any]:
    existing = load_json(path)
    if existing.get("run_id") == run_id:
        return existing
    return new_state(run_id, observed_at)


def persist(path: Path, state: dict[str, Any]) -> None:
    write_json(path, state)
