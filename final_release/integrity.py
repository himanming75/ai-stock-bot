from __future__ import annotations
from pathlib import Path
from typing import Any
from final_release.io import file_sha256

def verify_inventory(
    root: Path,
    inventory: dict[str, Any],
) -> dict[str, Any]:
    failures = []
    verified = 0
    for row in inventory.get("files", []):
        path = root / str(row.get("path", ""))
        if not path.exists():
            failures.append({
                "path": row.get("path"),
                "reason": "MISSING",
            })
            continue
        actual = file_sha256(path)
        if actual != row.get("sha256"):
            failures.append({
                "path": row.get("path"),
                "reason": "HASH_MISMATCH",
                "expected": row.get("sha256"),
                "actual": actual,
            })
            continue
        verified += 1
    return {
        "passed": not failures,
        "verified_file_count": verified,
        "expected_file_count": inventory.get("file_count", 0),
        "failures": failures,
    }
