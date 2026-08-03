from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from portfolio_scoring.models import Candidate


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    return value if isinstance(value, dict) else {}


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def parse_input(
    payload: dict[str, Any],
) -> tuple[list[Candidate], dict[str, Any]]:
    rows = payload.get("candidates", [])
    if not isinstance(rows, list):
        raise ValueError("candidates must be a list")

    candidates = [
        Candidate.from_dict(row)
        for row in rows
        if isinstance(row, dict)
    ]
    policy = payload.get("policy", {})
    if not isinstance(policy, dict):
        policy = {}
    return candidates, policy
