from __future__ import annotations


def performance_targets() -> dict:
    return {
        "market_polling_cycle_seconds_max": 30,
        "ai_decision_latency_ms_target": 500,
        "portfolio_allocation_latency_ms_target": 250,
        "ledger_write_latency_ms_target": 100,
        "full_cycle_latency_ms_target": 1500,
        "memory_growth_per_hour_mb_max": 50,
        "uncaught_exceptions_allowed": 0,
        "deadlocks_allowed": 0,
        "missed_cycles_allowed": 0,
        "minimum_long_run_hours": 8,
    }


def evaluate_fixture_metrics() -> dict:
    observed = {
        "market_polling_cycle_seconds": 30,
        "ai_decision_latency_ms": 120,
        "portfolio_allocation_latency_ms": 35,
        "ledger_write_latency_ms": 8,
        "full_cycle_latency_ms": 220,
        "memory_growth_per_hour_mb": 4,
        "uncaught_exceptions": 0,
        "deadlocks": 0,
        "missed_cycles": 0,
    }
    targets = performance_targets()
    checks = {
        "market_polling_cycle": (
            observed["market_polling_cycle_seconds"]
            <= targets["market_polling_cycle_seconds_max"]
        ),
        "ai_decision_latency": (
            observed["ai_decision_latency_ms"]
            <= targets["ai_decision_latency_ms_target"]
        ),
        "portfolio_latency": (
            observed["portfolio_allocation_latency_ms"]
            <= targets["portfolio_allocation_latency_ms_target"]
        ),
        "ledger_latency": (
            observed["ledger_write_latency_ms"]
            <= targets["ledger_write_latency_ms_target"]
        ),
        "full_cycle_latency": (
            observed["full_cycle_latency_ms"]
            <= targets["full_cycle_latency_ms_target"]
        ),
        "memory_growth": (
            observed["memory_growth_per_hour_mb"]
            <= targets["memory_growth_per_hour_mb_max"]
        ),
        "uncaught_exceptions": observed["uncaught_exceptions"] == 0,
        "deadlocks": observed["deadlocks"] == 0,
        "missed_cycles": observed["missed_cycles"] == 0,
    }
    return {
        "targets": targets,
        "observed_fixture_metrics": observed,
        "checks": checks,
        "fixture_performance_status": (
            "PASS" if all(checks.values()) else "BLOCKED"
        ),
        "actual_long_run_test_complete": False,
    }
