from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


class BuildManifestBuilder:
    def build(
        self,
        *,
        root: Path,
        files: list[Path],
        version: str,
    ) -> dict[str, Any]:
        entries = []
        for path in sorted(files):
            if not path.exists() or not path.is_file():
                continue
            entries.append({
                "path": str(path.relative_to(root)).replace("\\", "/"),
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            })
        raw = json.dumps(entries, sort_keys=True, separators=(",", ":"))
        return {
            "version": version,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "file_count": len(entries),
            "files": entries,
            "manifest_sha256": hashlib.sha256(
                raw.encode("utf-8")
            ).hexdigest(),
        }


class ReleaseManifestBuilder:
    def build(
        self,
        *,
        version: str,
        build_manifest: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "release_version": version,
            "build_manifest_sha256": build_manifest["manifest_sha256"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "release_state": "PREVIEW_ONLY",
            "actual_release_applied": False,
            "actual_service_installed": False,
            "actual_runtime_started": False,
        }


class VersionHistory:
    def __init__(self, path: Path) -> None:
        self.path = path

    def append(self, record: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
