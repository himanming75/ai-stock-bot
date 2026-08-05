from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any


TRACKED_ROOTS = (
    "broker_integration",
    "operations",
    "live_safety",
    "live_read",
    "live_execution",
    "live_reconciliation",
    "live_runtime",
    "live_qualification",
    "validation_control",
)


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build_release_manifest(root: Path) -> dict[str, Any]:
    files = []
    for rel_root in TRACKED_ROOTS:
        base = root / rel_root
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            files.append({
                "path": path.relative_to(root).as_posix(),
                "size_bytes": path.stat().st_size,
                "sha256": _file_hash(path),
            })

    canonical = json.dumps(files, sort_keys=True, separators=(",", ":"))
    return {
        "stage": "R1_RELEASE_MANIFEST",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tracked_root_count": len(TRACKED_ROOTS),
        "file_count": len(files),
        "files": files,
        "manifest_sha256": hashlib.sha256(
            canonical.encode("utf-8")
        ).hexdigest(),
        "immutable_after_production_approval": True,
    }
