from __future__ import annotations
from collections import defaultdict
from typing import Any

def matrix(plugins: list[dict[str, Any]]) -> dict[str, Any]:
    by_capability = defaultdict(list)
    rows = []
    for plugin in plugins:
        manifest = plugin.get("manifest", {})
        plugin_id = str(manifest.get("plugin_id", plugin.get("folder", "UNKNOWN")))
        caps = sorted(set(manifest.get("capabilities", [])))
        rows.append({
            "plugin_id": plugin_id,
            "enabled": manifest.get("enabled") is True,
            "capabilities": caps,
        })
        for capability in caps:
            by_capability[capability].append(plugin_id)
    return {
        "plugins": rows,
        "by_capability": dict(sorted(by_capability.items())),
    }
