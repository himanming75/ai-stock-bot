from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any


class IncidentSnapshotBuilder:
    def build(
        self,
        *,
        root: Path,
        sources: list[Path],
        output_dir: Path,
    ) -> dict[str, Any]:
        output_dir.mkdir(parents=True, exist_ok=True)
        captured = []

        for source in sources:
            if not source.exists() or not source.is_file():
                continue
            relative = str(source.relative_to(root)).replace("\\", "/")
            content = source.read_bytes()
            digest = hashlib.sha256(content).hexdigest()
            destination = output_dir / source.name
            destination.write_bytes(content)
            captured.append({
                "source": relative,
                "snapshot_file": destination.name,
                "size_bytes": len(content),
                "sha256": digest,
            })

        manifest = {
            "stage": "OPERATIONS_V2_INCIDENT_SNAPSHOT",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "captured_file_count": len(captured),
            "files": captured,
            "automatic_recovery_performed": False,
            "automatic_order_replay_performed": False,
        }
        (output_dir / "incident_manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return manifest
