from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any


class UpgradeRollbackManager:
    def build_manifest(
        self,
        *,
        root: Path,
        include_roots: list[str],
    ) -> dict[str, Any]:
        files = []
        for relative in include_roots:
            base = root / relative
            if not base.exists():
                continue
            for path in sorted(base.rglob("*")):
                if path.is_file() and "__pycache__" not in path.parts:
                    digest = hashlib.sha256(path.read_bytes()).hexdigest()
                    files.append({
                        "path": str(path.relative_to(root)).replace("\\", "/"),
                        "sha256": digest,
                        "size_bytes": path.stat().st_size,
                    })
        raw = json.dumps(files, sort_keys=True, separators=(",", ":"))
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "file_count": len(files),
            "files": files,
            "manifest_sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
            "actual_upgrade_performed": False,
            "actual_rollback_performed": False,
        }
