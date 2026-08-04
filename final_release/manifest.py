from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
from final_release.io import digest

MODULES = [
    "MARKET_REGIME",
    "META_STRATEGY",
    "PAPER_EXECUTION",
    "POSITION_LIFECYCLE",
    "ACCOUNT_RECONCILIATION",
    "BROKER_RECONCILIATION",
    "BACKTEST_BATCH",
    "PORTFOLIO_MANAGER",
    "AI_RISK_MANAGER",
    "RISK_BUDGET",
    "ADAPTIVE_REBALANCE",
    "MASTER_ORCHESTRATOR",
    "AUTONOMOUS_DECISION",
    "AUTONOMOUS_CYCLE",
    "MULTI_DAY_SCHEDULER",
    "CONTINUOUS_ENGINE",
    "CONTINUOUS_RUNTIME",
    "FINAL_SYSTEM_INTEGRATION",
]

def build_manifest(
    certificate: dict[str, Any],
    inventory: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    body = {
        "manifest_type": "FINAL_RELEASE_MANIFEST",
        "release_id": certificate.get("release_id"),
        "release_version": certificate.get("release_version"),
        "release_name": certificate.get("release_name"),
        "base_commit": policy.get("base_commit"),
        "branch": policy.get("branch", "main"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "module_count": len(MODULES),
        "modules": MODULES,
        "inventory_file_count": inventory.get("file_count"),
        "inventory_total_size_bytes": inventory.get("total_size_bytes"),
        "paper_only": True,
        "production_release_created": True,
        "live_trading_enabled": False,
        "broker_write_enabled": False,
        "order_submission_enabled": False,
        "manual_approval_required": True,
    }
    body["manifest_sha256"] = digest(body)
    return body
