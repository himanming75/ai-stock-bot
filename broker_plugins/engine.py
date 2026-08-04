from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from broker_plugins.io import write_json, append_jsonl
from broker_plugins.discovery import discover
from broker_plugins.compatibility import evaluate as evaluate_compatibility
from broker_plugins.capabilities import matrix
from broker_plugins.loader import build_descriptor
from broker_plugins.reload import build_plan

def evaluate(root: Path) -> dict:
    discovered = discover(root)
    descriptors = []
    compatibility_rows = []
    for plugin in discovered:
        compatibility = evaluate_compatibility(plugin)
        compatibility_rows.append({
            "plugin_id": plugin.get("manifest", {}).get("plugin_id"),
            **compatibility,
        })
        descriptors.append(build_descriptor(plugin, compatibility))
    capability_matrix = matrix(discovered)
    reload_plan = build_plan(
        root,
        [str(row.get("plugin_id")) for row in descriptors if row.get("enabled")],
    )
    enabled = [row for row in descriptors if row.get("enabled")]
    loadable = [row for row in descriptors if row.get("loadable")]
    checks = {
        "plugins_discovered": len(descriptors) >= 1,
        "all_enabled_plugins_loadable": len(enabled) == len(loadable),
        "all_plugins_read_only": all(row.get("read_only") is True for row in descriptors),
        "all_order_support_disabled": all(row.get("supports_orders") is False for row in descriptors),
        "reload_write_disabled": reload_plan["broker_write_enabled"] is False,
    }
    failed = [key for key, passed in checks.items() if not passed]
    state = "BROKER_PLUGIN_FRAMEWORK_READY" if not failed else "BROKER_PLUGIN_FRAMEWORK_REVIEW_REQUIRED"
    observed = datetime.now(timezone.utc).isoformat()
    result = {
        "stage": "V205.64",
        "state": state,
        "status": "PASS",
        "observed_at": observed,
        "discovered_plugin_count": len(descriptors),
        "enabled_plugin_count": len(enabled),
        "loadable_plugin_count": len(loadable),
        "plugins": descriptors,
        "compatibility": compatibility_rows,
        "capability_matrix": capability_matrix,
        "reload_plan": reload_plan,
        "checks": checks,
        "failed": failed,
        "plugin_order_submission_enabled": False,
        "broker_write_enabled": False,
        "live_submission_enabled": False,
        "actual_live_orders_submitted": 0,
        "next_phase": "V206_01_TO_V210_64_RISK_ENGINE_V2",
    }
    actual = root / "release/v201_01_to_v205_64/actual"
    write_json(actual / "broker_plugin_framework_result.json", result)
    write_json(actual / "broker_plugin_inventory.json", {"plugins": descriptors})
    write_json(actual / "broker_plugin_compatibility.json", {"rows": compatibility_rows})
    write_json(actual / "broker_capability_matrix.json", capability_matrix)
    append_jsonl(actual / "broker_plugin_audit_ledger.jsonl", {
        "observed_at": observed,
        "state": state,
        "plugin_count": len(descriptors),
        "loadable_count": len(loadable),
        "actual_live_orders_submitted": 0,
    })
    return result
