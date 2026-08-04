from __future__ import annotations
from typing import Any

REQUIRED_METHODS = [
    "connect", "disconnect", "get_account",
    "get_positions", "get_orders", "health", "capabilities",
]

def build_descriptor(plugin: dict[str, Any], compatibility: dict[str, Any]) -> dict[str, Any]:
    manifest = plugin.get("manifest", {})
    return {
        "plugin_id": manifest.get("plugin_id"),
        "display_name": manifest.get("display_name"),
        "version": manifest.get("version"),
        "api_version": manifest.get("api_version"),
        "enabled": manifest.get("enabled") is True,
        "loadable": plugin.get("loadable") is True and compatibility.get("compatible") is True,
        "read_only": True,
        "supports_orders": False,
        "required_methods": REQUIRED_METHODS,
        "capabilities": manifest.get("capabilities", []),
        "actual_live_orders_submitted": 0,
    }

def submit_order(_: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": False,
        "error": "PLUGIN_ORDER_SUBMISSION_DISABLED",
        "actual_live_orders_submitted": 0,
    }
