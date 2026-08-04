from __future__ import annotations
from pathlib import Path
from typing import Any
from master_ai_orchestrator.io import load_json

MODULES = [
    {
        "module_id": "MARKET_REGIME",
        "path": "release/v93_33_to_v93_64/actual/multi_timeframe_regime_result.json",
        "allowed_states": ["MULTI_TIMEFRAME_REGIME_READY"],
        "required": True,
    },
    {
        "module_id": "META_STRATEGY",
        "path": "release/v94_01_to_v94_32/actual/meta_strategy_result.json",
        "allowed_states": ["META_STRATEGY_ENGINE_READY"],
        "required": True,
    },
    {
        "module_id": "PAPER_ACCOUNT",
        "path": "release/v96_01_to_v96_32/actual/paper_account_reconciliation_result.json",
        "allowed_states": ["PAPER_ACCOUNT_RECONCILIATION_PASS"],
        "required": True,
    },
    {
        "module_id": "PORTFOLIO_MANAGER",
        "path": "release/v99_01_to_v99_32/actual/ai_portfolio_manager_result.json",
        "allowed_states": ["AI_PORTFOLIO_MANAGER_READY"],
        "required": True,
    },
    {
        "module_id": "AI_RISK_MANAGER",
        "path": "release/v100_01_to_v100_32/actual/ai_risk_manager_result.json",
        "allowed_states": ["AI_RISK_MANAGER_READY"],
        "required": True,
    },
    {
        "module_id": "RISK_BUDGET",
        "path": "release/v100_33_to_v100_64/actual/risk_budget_allocation_result.json",
        "allowed_states": ["RISK_BUDGET_ALLOCATION_READY"],
        "required": True,
    },
    {
        "module_id": "REBALANCE_CONTROL",
        "path": "release/v101_01_to_v101_32/actual/portfolio_rebalance_control_result.json",
        "allowed_states": [
            "PORTFOLIO_REBALANCE_CONTROL_READY",
            "PORTFOLIO_REBALANCE_CONTROL_NO_ACTION",
        ],
        "required": True,
    },
    {
        "module_id": "ADAPTIVE_REBALANCE",
        "path": "release/v101_33_to_v101_64/actual/adaptive_rebalance_optimization_result.json",
        "allowed_states": [
            "ADAPTIVE_REBALANCE_OPTIMIZATION_READY",
            "ADAPTIVE_REBALANCE_OPTIMIZATION_NO_ACTION",
        ],
        "required": True,
    },
]

def collect_modules(root: Path) -> list[dict[str, Any]]:
    rows = []
    for spec in MODULES:
        result = load_json(root / spec["path"])
        state = result.get("state")
        status = result.get("status")
        present = bool(result)
        ready = present and status == "PASS" and state in spec["allowed_states"]
        rows.append({
            "module_id": spec["module_id"],
            "source_path": spec["path"],
            "required": spec["required"],
            "present": present,
            "state": state,
            "status": status,
            "ready": ready,
            "certificate_present": any(
                str(key).endswith("_sha256") and len(str(value)) == 64
                for key, value in result.items()
            ),
        })
    return rows
