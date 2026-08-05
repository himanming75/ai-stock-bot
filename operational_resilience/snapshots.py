from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any


class StateSnapshotManager:
    def create(
        self,
        *,
        output: Path,
        state: dict[str, Any],
        source_name: str,
    ) -> dict[str, Any]:
        output.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "snapshot_schema_version": 1,
            "source_name": source_name,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "state": state,
            "actual_restore_performed": False,
        }
        raw = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        digest = hashlib.sha256(raw).hexdigest()
        payload["sha256"] = digest
        output.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return payload

    def verify(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        expected = snapshot.get("sha256", "")
        payload = dict(snapshot)
        payload.pop("sha256", None)
        raw = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        actual = hashlib.sha256(raw).hexdigest()
        return {
            "expected_sha256": expected,
            "actual_sha256": actual,
            "integrity_valid": expected == actual,
        }


class StateMigrationPreview:
    def preview(
        self,
        *,
        current_version: int,
        target_version: int,
        state: dict[str, Any],
    ) -> dict[str, Any]:
        blockers = []
        if target_version <= current_version:
            blockers.append("TARGET_VERSION_MUST_BE_HIGHER")
        if not isinstance(state, dict):
            blockers.append("STATE_MUST_BE_OBJECT")

        return {
            "current_version": current_version,
            "target_version": target_version,
            "blockers": blockers,
            "migration_preview_allowed": not blockers,
            "actual_migration_performed": False,
            "actual_state_modified": False,
            "operator_approval_required": True,
        }
