from __future__ import annotations
from .integrity import canonical_hash


def verify_replay(record: dict) -> dict:
    core = {
        "context_summary": record["context_summary"],
        "arbitration": record["arbitration"],
        "constraints": record["constraints"],
        "paper_order_candidate": record["paper_order_candidate"],
    }
    calculated = canonical_hash(core)
    expected = record.get("decision_hash")
    return {
        "valid": calculated == expected,
        "expected_hash": expected,
        "calculated_hash": calculated,
    }
