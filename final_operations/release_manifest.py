from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any


TRACKED_ROOTS = (
    "configuration_profiles",
    "runtime_configuration",
    "runtime_session",
    "runtime_core",
    "broker_platform",
    "final_operations",
    "deployment",
    "operations",
    "tools",
)


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_release_manifest(root: Path) -> dict[str, Any]:
    files = []
    for relative_root in TRACKED_ROOTS:
        base = root / relative_root
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file():
                continue
            if "__pycache__" in path.parts:
                continue
            files.append({
                "path": str(path.relative_to(root)).replace("\\", "/"),
                "size_bytes": path.stat().st_size,
                "sha256": _hash_file(path),
            })

    raw = json.dumps(files, sort_keys=True, separators=(",", ":"))
    return {
        "stage": "R15_RELEASE_MANIFEST",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tracked_file_count": len(files),
        "files": files,
        "manifest_sha256": hashlib.sha256(
            raw.encode("utf-8")
        ).hexdigest(),
        "actual_release_performed": False,
    }
