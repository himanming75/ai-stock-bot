from __future__ import annotations
import json
from pathlib import Path


def append_candidate(path: Path, candidate: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(
            {
                "symbol": candidate.get("symbol"),
                "action": candidate.get("action"),
                "confidence": candidate.get("confidence"),
                "score": candidate.get("score"),
                "regime": candidate.get("regime"),
                "trend": candidate.get("trend"),
                "risk_gate": candidate.get("risk_gate"),
                "execution_mode": candidate.get("execution_mode"),
                "broker_write_enabled": False,
                "order_submission_enabled": False,
            },
            sort_keys=True,
        ) + "\n")
