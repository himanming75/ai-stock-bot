from __future__ import annotations
from typing import Any

DEPENDENCIES = {
    "META_STRATEGY": ["MARKET_REGIME"],
    "PORTFOLIO_MANAGER": ["META_STRATEGY"],
    "AI_RISK_MANAGER": ["PORTFOLIO_MANAGER"],
    "RISK_BUDGET": ["AI_RISK_MANAGER"],
    "REBALANCE_CONTROL": ["PORTFOLIO_MANAGER", "RISK_BUDGET", "PAPER_ACCOUNT"],
    "ADAPTIVE_REBALANCE": ["REBALANCE_CONTROL", "RISK_BUDGET", "MARKET_REGIME"],
}

def evaluate_dependencies(modules: list[dict[str, Any]]) -> dict[str, Any]:
    ready = {row["module_id"]: bool(row["ready"]) for row in modules}
    details = {}
    for module_id, deps in DEPENDENCIES.items():
        checks = {dep: ready.get(dep, False) for dep in deps}
        details[module_id] = {
            "dependencies": deps,
            "checks": checks,
            "passed": all(checks.values()),
        }
    failed = [name for name, row in details.items() if not row["passed"]]
    return {"passed": not failed, "failed": failed, "details": details}
