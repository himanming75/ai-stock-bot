from __future__ import annotations
from pathlib import Path
from typing import Any
from broker_plugins.io import load_json
from broker_plugins.spec import validate_manifest

def discover(root: Path) -> list[dict[str, Any]]:
    plugins_root = root / "broker_plugin_packages"
    rows = []
    if not plugins_root.exists():
        return rows
    for folder in sorted(p for p in plugins_root.iterdir() if p.is_dir()):
        manifest_path = folder / "manifest.json"
        manifest = load_json(manifest_path)
        validation = validate_manifest(manifest)
        rows.append({
            "folder": folder.name,
            "manifest_path": str(manifest_path.relative_to(root)).replace("\\", "/"),
            "manifest": manifest,
            "validation": validation,
            "loadable": validation["valid"] and manifest.get("enabled") is True,
        })
    return rows
