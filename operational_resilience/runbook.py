from __future__ import annotations
from datetime import datetime, timezone
from typing import Any


class RecoveryRunbookGenerator:
    def build(self, fault_results: list[dict[str, Any]]) -> dict[str, Any]:
        steps = []
        for item in fault_results:
            steps.append({
                "fault_type": item["fault_type"],
                "detect": f"Confirm {item['fault_type']} signal",
                "contain": "Keep broker write and automatic orders disabled",
                "diagnose": item["expected_response"],
                "recover": "Operator-reviewed recovery preview only",
                "verify": "Run offline tests and integrity verification",
            })

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "step_count": len(steps),
            "steps": steps,
            "automatic_recovery_enabled": False,
            "actual_recovery_performed": False,
        }
