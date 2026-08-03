from __future__ import annotations

from pathlib import Path
from typing import Any


MODULE_ALTERNATIVES = {
    "indicator_engine": ["indicator_engine", "indicator_engine_v2"],
    "strategy_engine": ["strategy_engine_v2"],
    "portfolio_scoring": ["portfolio_scoring"],
    "explainability": ["explainability_engine"],
    "backtest": ["backtest_v2"],
    "validation": ["validation_v2"],
    "multi_asset": ["multi_asset_backtest"],
    "orchestrator": ["paper_orchestrator"],
    "web_ui": ["web_ui_v2"],
}


def discover_layout(root: Path) -> dict[str, Any]:
    modules = {}
    missing = []
    for logical_name, candidates in MODULE_ALTERNATIVES.items():
        selected = next(
            (candidate for candidate in candidates if (root / candidate).is_dir()),
            "",
        )
        modules[logical_name] = selected
        if not selected:
            missing.append(logical_name)

    return {
        "modules": modules,
        "missing_modules": missing,
        "layout_valid": not missing,
        "indicator_layout": modules.get("indicator_engine", ""),
    }
