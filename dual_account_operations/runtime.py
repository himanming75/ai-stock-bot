from __future__ import annotations
import json
from pathlib import Path


class RuntimeProfileStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def save(self, profile_name: str) -> None:
        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        self.path.write_text(
            json.dumps(
                {
                    "active_profile": profile_name,
                    "schema_version": 1,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

    def load(self) -> str:
        if not self.path.exists():
            return "ALL_STOP"
        payload = json.loads(
            self.path.read_text(
                encoding="utf-8-sig"
            )
        )
        return str(
            payload.get(
                "active_profile",
                "ALL_STOP",
            )
        ).upper()
