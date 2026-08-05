from __future__ import annotations
import hashlib
import json
from pathlib import Path
import zipfile
from typing import Any


class ReleaseBundleBuilder:
    def build_preview(
        self,
        *,
        root: Path,
        output: Path,
        files: list[Path],
    ) -> dict[str, Any]:
        output.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(files):
                if path.exists() and path.is_file():
                    archive.write(path, path.relative_to(root))
        digest = hashlib.sha256(output.read_bytes()).hexdigest()
        return {
            "bundle_path": str(output),
            "bundle_size_bytes": output.stat().st_size,
            "bundle_sha256": digest,
            "file_count": len([
                path for path in files if path.exists() and path.is_file()
            ]),
            "bundle_created_for_preview": True,
            "actual_install_performed": False,
            "actual_release_applied": False,
        }


class BundleIntegrityVerifier:
    def verify(self, *, bundle_path: Path, expected_sha256: str) -> dict[str, Any]:
        actual = hashlib.sha256(bundle_path.read_bytes()).hexdigest()
        return {
            "expected_sha256": expected_sha256,
            "actual_sha256": actual,
            "integrity_valid": actual == expected_sha256,
        }
