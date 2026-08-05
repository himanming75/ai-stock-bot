from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any


class IncidentReproductionBundle:
    def build(
        self,
        *,
        root: Path,
        output: Path,
        sources: list[Path],
    ) -> dict[str, Any]:
        output.mkdir(parents=True, exist_ok=True)
        files = []
        for source in sources:
            if not source.exists() or not source.is_file():
                continue
            data = source.read_bytes()
            target = output / source.name
            target.write_bytes(data)
            files.append({
                "source": str(source.relative_to(root)).replace("\\", "/"),
                "snapshot": target.name,
                "sha256": hashlib.sha256(data).hexdigest(),
                "size_bytes": len(data),
            })

        manifest = {
            "stage": "VALIDATION_INCIDENT_REPRODUCTION",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "file_count": len(files),
            "files": files,
            "credentials_included": False,
            "automatic_recovery_performed": False,
            "automatic_retry_performed": False,
        }
        (output / "incident_manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return manifest
