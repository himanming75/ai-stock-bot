from __future__ import annotations
from typing import Any


class FaultInjectionSimulator:
    SUPPORTED = {
        "NETWORK_TIMEOUT",
        "RATE_LIMIT",
        "CORRUPT_LEDGER_LINE",
        "WORKER_FAILURE",
        "DISK_SPACE_WARNING",
        "STALE_CONFIGURATION",
    }

    def simulate(self, fault_type: str) -> dict[str, Any]:
        if fault_type not in self.SUPPORTED:
            raise ValueError("UNSUPPORTED_FAULT_TYPE")

        expected = {
            "NETWORK_TIMEOUT": "READ_ONLY_RETRY_PREVIEW",
            "RATE_LIMIT": "RATE_LIMIT_HOLD_PREVIEW",
            "CORRUPT_LEDGER_LINE": "LEDGER_AUDIT_FAILURE",
            "WORKER_FAILURE": "RECOVERY_QUEUE_PREVIEW",
            "DISK_SPACE_WARNING": "RETENTION_AND_ARCHIVE_PREVIEW",
            "STALE_CONFIGURATION": "CONFIGURATION_RELOAD_PREVIEW",
        }[fault_type]

        return {
            "fault_type": fault_type,
            "expected_response": expected,
            "fault_injected_into_live_runtime": False,
            "actual_recovery_performed": False,
            "actual_network_used": False,
            "actual_order_submission_performed": False,
        }
