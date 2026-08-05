from __future__ import annotations
import json
from pathlib import Path
from typing import Any


def evaluate_paper_completion(root: Path) -> dict[str, Any]:
    p5_actual = (
        root / "release/p5_paper_long_run_qualification/actual/"
               "p5_actual_qualification.json"
    )
    if not p5_actual.exists():
        return {
            "paper_complete": False,
            "certificate_present": False,
            "reason": "P5_ACTUAL_QUALIFICATION_MISSING",
        }

    value = json.loads(p5_actual.read_text(encoding="utf-8-sig"))
    complete = (
        value.get("actual_paper_long_run_qualified") is True
        and value.get("paper_complete") is True
    )
    return {
        "paper_complete": complete,
        "certificate_present": True,
        "reason": "PASS" if complete else "P5_ACTUAL_NOT_COMPLETE",
    }
