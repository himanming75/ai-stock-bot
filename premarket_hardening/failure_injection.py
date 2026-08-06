from __future__ import annotations


SCENARIOS = {
    "NETWORK_TIMEOUT": {
        "expected_action": "WAIT",
        "expected_recovery": "RETRY_BACKOFF",
        "critical": False,
    },
    "MARKET_DATA_STALE": {
        "expected_action": "ALL_STOP",
        "expected_recovery": "MANUAL_REVIEW",
        "critical": True,
    },
    "LEDGER_WRITE_FAILURE": {
        "expected_action": "ALL_STOP",
        "expected_recovery": "REPAIR_LEDGER",
        "critical": True,
    },
    "CORRUPT_CHECKPOINT": {
        "expected_action": "ALL_STOP",
        "expected_recovery": "SAFE_DEFAULT_RESTORE",
        "critical": True,
    },
    "BROKER_RATE_LIMIT": {
        "expected_action": "WAIT",
        "expected_recovery": "EXPONENTIAL_BACKOFF",
        "critical": False,
    },
    "PROCESS_TERMINATION": {
        "expected_action": "ALL_STOP",
        "expected_recovery": "WATCHDOG_RESTART",
        "critical": True,
    },
}


def execute_fixture_scenario(name: str) -> dict:
    if name not in SCENARIOS:
        return {
            "status": "BLOCKED",
            "reason": "UNKNOWN_SCENARIO",
        }

    scenario = SCENARIOS[name]
    return {
        "status": "PASS",
        "scenario": name,
        "observed_action": scenario["expected_action"],
        "recovery_path": scenario["expected_recovery"],
        "critical": scenario["critical"],
        "network_used": False,
        "process_killed": False,
        "disk_modified": False,
    }
