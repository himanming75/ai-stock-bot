from __future__ import annotations
from typing import Any

def deduplicate_intents(
    intents: list[dict[str, Any]],
    prior_ledger: list[dict[str, Any]],
) -> dict[str, Any]:
    prior_keys = {
        str(row.get("intent_key", ""))
        for row in prior_ledger
        if row.get("intent_key")
    }
    unique = []
    duplicates = []
    seen = set()

    for row in intents:
        key = str(row.get("intent_key", ""))
        if key in prior_keys or key in seen:
            item = dict(row)
            item["state"] = "BLOCKED_DUPLICATE"
            duplicates.append(item)
            continue
        seen.add(key)
        unique.append(row)

    return {
        "unique_intents": unique,
        "duplicate_intents": duplicates,
        "duplicate_count": len(duplicates),
    }
