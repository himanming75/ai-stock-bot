from __future__ import annotations
from .integrity import canonical_hash


def verify(record: dict) -> dict:
    calculated = canonical_hash(record["proposal"])
    expected = record.get("proposal_hash")
    return {
        "valid": calculated == expected,
        "expected_hash": expected,
        "calculated_hash": calculated,
    }
