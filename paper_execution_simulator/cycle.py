from __future__ import annotations
import hashlib
import json
from typing import Any

def build_cycle_id(source: dict[str, Any], simulation_date: str) -> str:
    payload = {
        "source_certificate": source.get("decision_orchestration_certificate_sha256"),
        "source_decision": source.get("source_paper_decision"),
        "simulation_date": simulation_date,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24]

def read_completed_cycles(lines: list[str]) -> set[str]:
    output = set()
    for line in lines:
        try:
            value = json.loads(line)
        except Exception:
            continue
        cycle_id = value.get("cycle_id")
        if cycle_id and value.get("cycle_state") == "COMPLETED":
            output.add(str(cycle_id))
    return output
