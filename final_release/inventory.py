from __future__ import annotations
from pathlib import Path
from typing import Any
from final_release.io import file_sha256

EXCLUDED_PARTS = {
    ".git", ".venv", "__pycache__", ".pytest_cache",
    "V105_33_TO_V105_64_FINAL_RELEASE_BUNDLE.zip",
}

VOLATILE_GENERATED_FILES = {
    "release/v105_33_to_v105_64/actual/final_file_inventory.json",
    "release/v105_33_to_v105_64/actual/final_integrity_audit.json",
    "release/v105_33_to_v105_64/actual/final_acceptance_test.json",
    "release/v105_33_to_v105_64/actual/production_readiness_final_release_result.json",
    "release/v105_33_to_v105_64/actual/final_release_ledger.jsonl",
    "release/v105_33_to_v105_64/bundle/AI_STOCK_BOT_V105_FINAL_RELEASE_BUNDLE.zip",
}

def should_include(path: Path, root: Path) -> bool:
    rel = path.relative_to(root)
    rel_text = rel.as_posix()
    if any(part in EXCLUDED_PARTS for part in rel.parts):
        return False
    if rel_text in VOLATILE_GENERATED_FILES:
        return False
    if path.suffix in {".pyc", ".pyo"}:
        return False
    return path.is_file()

def build_inventory(root: Path) -> dict[str, Any]:
    rows = []
    for path in sorted(root.rglob("*")):
        if not should_include(path, root):
            continue
        rel = path.relative_to(root).as_posix()
        rows.append({
            "path": rel,
            "size_bytes": path.stat().st_size,
            "sha256": file_sha256(path),
        })
    return {
        "file_count": len(rows),
        "total_size_bytes": sum(row["size_bytes"] for row in rows),
        "files": rows,
    }
