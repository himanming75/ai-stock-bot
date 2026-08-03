from __future__ import annotations
from pathlib import Path
from typing import Any
from dashboard_analytics_v3.io import load_json

SOURCES = {
    "strategy": "release/v89_01_to_v89_32/actual/v89_result.json",
    "portfolio": "release/v89_33_to_v89_64/actual/portfolio_optimization_result.json",
    "multi_day": "release/v83_77_to_v83_80/actual/multi_day_paper_validation_result.json",
    "production_release": "release/v88_17_to_v88_24/actual/paper_production_release_result.json",
    "orchestrator": "release/v88_09_to_v88_16/actual/paper_orchestrator_result.json",
    "robustness": "release/v87_09_to_v87_16/actual/walk_forward_stress_validation_result.json",
}

def collect(root: Path) -> dict[str, Any]:
    raw = {name: load_json(root / rel) for name, rel in SOURCES.items()}
    strategy = raw["strategy"]
    portfolio = raw["portfolio"].get("portfolio_optimization", {})
    multi_day = raw["multi_day"]
    release = raw["production_release"]

    rankings = strategy.get("strategy_rankings", [])
    strategy_rows = []
    for row in rankings:
        gate = row.get("gate", {})
        strategy_rows.append({
            "rank": row.get("rank"),
            "strategy": row.get("strategy", ""),
            "return_pct": row.get("total_return_pct", 0),
            "drawdown_pct": row.get("maximum_drawdown_pct", 0),
            "sharpe": row.get("sharpe_ratio", 0),
            "profit_factor": row.get("profit_factor", 0),
            "win_rate_pct": row.get("win_rate_pct", 0),
            "trades": row.get("total_trades", 0),
            "excess_return_pct": gate.get("excess_return_pct", 0),
            "approved": gate.get("approved", False),
            "failed_checks": gate.get("failed", []),
            "score": row.get("score", 0),
        })

    allocations = portfolio.get("allocations", [])
    risk = portfolio.get("risk", {})
    completed = int(multi_day.get("completed_days", 0))
    required = int(multi_day.get("minimum_days", 3))
    remaining = max(0, required - completed)

    alerts = []
    for row in strategy_rows:
        if row["failed_checks"]:
            alerts.append({
                "level": "warning",
                "title": f'{row["strategy"]} performance gate',
                "message": ", ".join(row["failed_checks"]),
            })
    for item in risk.get("failed", []):
        alerts.append({
            "level": "danger",
            "title": "Portfolio risk gate",
            "message": item,
        })
    if remaining:
        alerts.append({
            "level": "info",
            "title": "Multi-day validation",
            "message": f"{remaining} additional distinct day(s) required.",
        })

    return {
        "stage": "V90.32",
        "stage_range": "V90.01-V90.32",
        "state": "DASHBOARD_ANALYTICS_V3_READY",
        "status": "PASS",
        "sources_available": {name: bool(value) for name, value in raw.items()},
        "strategy_state": strategy.get("state", "NOT_AVAILABLE"),
        "portfolio_state": raw["portfolio"].get("state", "NOT_AVAILABLE"),
        "production_release_state": release.get("state", "NOT_AVAILABLE"),
        "orchestrator_state": raw["orchestrator"].get("state", "NOT_AVAILABLE"),
        "strategy_rows": strategy_rows,
        "allocations": allocations,
        "portfolio_risk": risk,
        "validation_progress": {
            "completed_days": completed,
            "required_days": required,
            "remaining_days": remaining,
            "percent_complete": round(min(100.0, completed / required * 100.0), 2) if required else 0,
        },
        "alerts": alerts,
        "benchmark_return_pct": strategy.get("benchmark", {}).get("total_return_pct", 0),
        "historical_input": strategy.get("historical_input"),
        "bar_count": strategy.get("bar_count", 0),
        "paper_only": True,
        "broker_write_enabled": False,
        "order_submission_enabled": False,
        "live_trading_enabled": False,
        "external_network_enabled": False,
    }
