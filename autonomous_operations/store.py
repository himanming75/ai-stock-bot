from __future__ import annotations
import json
from pathlib import Path


class CheckpointStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def save(self, payload: dict) -> None:
        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        self.path.write_text(
            json.dumps(
                payload,
                indent=2,
                sort_keys=True,
            ) + "\n",
            encoding="utf-8",
        )

    def load(self) -> dict:
        if not self.path.exists():
            return {
                "cycle_sequence": 0,
                "last_cycle_id": None,
                "last_status": "SAFE_DEFAULT",
                "last_action": "WAIT",
                "emergency_stop": True,
            }

        return json.loads(
            self.path.read_text(
                encoding="utf-8-sig"
            )
        )
