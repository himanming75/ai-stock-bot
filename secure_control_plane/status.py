from __future__ import annotations
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


class OperationalStatusAggregator:
    def collect(self, root: Path) -> dict[str, Any]:
        p2 = read_json(
            root / "release/p2_actual_paper_broker_read/actual/"
                   "p2_actual_broker_read_result.json"
        )
        monitoring = read_json(
            root / "release/ai_monitoring_distributed_runtime/actual/"
                   "ai_monitoring_distributed_runtime_result.json"
        )
        resilience = read_json(
            root / "release/operational_resilience_data_governance/actual/"
                   "operational_resilience_result.json"
        )
        shadow = read_json(
            root / "release/shadow_trading_production_approval/actual/"
                   "shadow_trading_production_approval_result.json"
        )

        return {
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "p2_status": p2.get("status", "UNKNOWN"),
            "p2_validated": p2.get("validated", False),
            "paper_endpoint": p2.get("paper_endpoint", ""),
            "monitoring_status": monitoring.get("status", "UNKNOWN"),
            "runtime_health": (
                monitoring.get("runtime_health", {}).get("status", "UNKNOWN")
            ),
            "operational_resilience_status": resilience.get(
                "status", "UNKNOWN"
            ),
            "release_gate": shadow.get("release_gate", "UNKNOWN"),
            "broker_write_enabled": False,
            "automatic_order_submission_enabled": False,
            "live_trading_enabled": False,
        }
