from __future__ import annotations

import json
from pathlib import Path


def validate_json(path: Path) -> dict:
    record = {
        "path": str(path),
        "exists": path.exists(),
        "valid": False,
        "error": None,
        "size_bytes": path.stat().st_size if path.exists() else 0,
    }
    if not path.exists():
        record["error"] = "FILE_MISSING"
        return record
    try:
        json.loads(path.read_text(encoding="utf-8-sig"))
        record["valid"] = True
    except Exception as exc:
        record["error"] = f"{type(exc).__name__}:{exc}"
    return record


def validate_jsonl(path: Path, *, tail_limit: int = 5000) -> dict:
    record = {
        "path": str(path),
        "exists": path.exists(),
        "valid": False,
        "line_count": 0,
        "invalid_line_count": 0,
        "invalid_lines": [],
        "size_bytes": path.stat().st_size if path.exists() else 0,
    }
    if not path.exists():
        record["invalid_lines"] = ["FILE_MISSING"]
        return record

    lines = path.read_text(
        encoding="utf-8-sig", errors="replace"
    ).splitlines()
    selected = lines[-tail_limit:]
    offset = max(0, len(lines) - len(selected))
    record["line_count"] = len(lines)

    for index, line in enumerate(selected, start=offset + 1):
        if not line.strip():
            continue
        try:
            json.loads(line)
        except Exception as exc:
            record["invalid_line_count"] += 1
            if len(record["invalid_lines"]) < 20:
                record["invalid_lines"].append(
                    {
                        "line": index,
                        "error": f"{type(exc).__name__}:{exc}",
                    }
                )

    record["valid"] = record["invalid_line_count"] == 0
    return record


def read_json_optional(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}
