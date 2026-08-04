from __future__ import annotations
import sys
from typing import Any

FRAMEWORK_API_VERSION = "1"
MINIMUM_PYTHON = (3, 10)

def evaluate(plugin: dict[str, Any]) -> dict[str, Any]:
    manifest = plugin.get("manifest", {})
    checks = {
        "python_version": sys.version_info >= MINIMUM_PYTHON,
        "api_version": str(manifest.get("api_version", "")) == FRAMEWORK_API_VERSION,
        "read_only": manifest.get("read_only") is True,
        "orders_disabled": manifest.get("supports_orders") is False,
        "manifest_valid": plugin.get("validation", {}).get("valid") is True,
    }
    failed = [key for key, passed in checks.items() if not passed]
    return {"compatible": not failed, "checks": checks, "failed": failed}
