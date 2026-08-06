from __future__ import annotations
import json
from pathlib import Path
from typing import Any


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "_available": False,
            "_path": str(path),
            "_error": "FILE_NOT_FOUND",
        }
    try:
        payload = json.loads(
            path.read_text(encoding="utf-8")
        )
        if not isinstance(payload, dict):
            return {
                "_available": False,
                "_path": str(path),
                "_error": "JSON_ROOT_NOT_OBJECT",
            }
        return {
            "_available": True,
            "_path": str(path),
            **payload,
        }
    except Exception as exc:
        return {
            "_available": False,
            "_path": str(path),
            "_error": str(exc),
        }


def read_jsonl_tail(
    path: Path,
    *,
    limit: int = 20,
) -> dict[str, Any]:
    if not path.exists():
        return {
            "available": False,
            "path": str(path),
            "items": [],
            "error": "FILE_NOT_FOUND",
        }
    try:
        lines = path.read_text(
            encoding="utf-8",
            errors="replace",
        ).splitlines()
        items = []
        for line in lines[-max(limit, 1):]:
            try:
                value = json.loads(line)
                items.append(value)
            except Exception:
                items.append({
                    "_raw": line,
                    "_parse_error": True,
                })
        return {
            "available": True,
            "path": str(path),
            "items": items,
            "line_count": len(lines),
            "error": None,
        }
    except Exception as exc:
        return {
            "available": False,
            "path": str(path),
            "items": [],
            "error": str(exc),
        }
