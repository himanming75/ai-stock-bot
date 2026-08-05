from __future__ import annotations
import hashlib
import json
from pathlib import Path
from typing import Any


class LedgerIntegrityAuditor:
    def audit(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            return {
                "path": str(path),
                "exists": False,
                "line_count": 0,
                "valid_json_lines": 0,
                "invalid_json_lines": [],
                "sha256": "",
                "status": "MISSING",
            }

        data = path.read_bytes()
        invalid = []
        valid = 0
        lines = path.read_text(
            encoding="utf-8-sig"
        ).splitlines()

        for index, line in enumerate(lines, start=1):
            if not line.strip():
                continue
            try:
                json.loads(line)
                valid += 1
            except Exception:
                invalid.append(index)

        return {
            "path": str(path),
            "exists": True,
            "line_count": len(lines),
            "valid_json_lines": valid,
            "invalid_json_lines": invalid,
            "sha256": hashlib.sha256(data).hexdigest(),
            "status": "PASS" if not invalid else "FAIL",
        }
