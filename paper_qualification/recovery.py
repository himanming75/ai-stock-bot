from __future__ import annotations
from typing import Any

def evaluate(events: list[dict[str, Any]]) -> dict[str, Any]:
    failures = [row for row in events if row.get("recovery_status") == "FAILED"]
    duplicates = [row for row in events if row.get("duplicate_order") is True]
    unresolved = [row for row in events if row.get("resolved") is False]
    return {
        "recovery_failures": len(failures),
        "duplicate_orders": len(duplicates),
        "unresolved_mismatches": len(unresolved),
        "recovery_passed": not failures and not duplicates and not unresolved,
    }
