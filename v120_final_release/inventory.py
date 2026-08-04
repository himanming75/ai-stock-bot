from __future__ import annotations
from pathlib import Path
from typing import Any
from v120_final_release.io import file_sha256

EXCLUDED_PARTS={".git",".venv","__pycache__",".pytest_cache"}
VOLATILE={
"release/v120_final/actual/project_inventory.json",
"release/v120_final/actual/integrity_audit.json",
"release/v120_final/actual/v120_final_release_result.json",
"release/v120_final/actual/v120_release_ledger.jsonl",
"release/v120_final/bundle/AI_STOCK_BOT_V120_FINAL.zip",
}

def build_inventory(root: Path) -> dict[str, Any]:
    rows=[]
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        rel=p.relative_to(root).as_posix()
        if any(part in EXCLUDED_PARTS for part in p.relative_to(root).parts):
            continue
        if rel in VOLATILE or p.suffix in {".pyc",".pyo"}:
            continue
        rows.append({"path":rel,"size_bytes":p.stat().st_size,"sha256":file_sha256(p)})
    return {
        "file_count":len(rows),
        "total_size_bytes":sum(r["size_bytes"] for r in rows),
        "files":rows,
    }

def verify_inventory(root: Path, inventory: dict[str, Any]) -> dict[str, Any]:
    failures=[]
    for row in inventory.get("files",[]):
        p=root/row["path"]
        if not p.exists():
            failures.append({"path":row["path"],"reason":"MISSING"})
        elif file_sha256(p)!=row["sha256"]:
            failures.append({"path":row["path"],"reason":"HASH_MISMATCH"})
    return {
        "passed":not failures,
        "verified_file_count":inventory.get("file_count",0)-len(failures),
        "expected_file_count":inventory.get("file_count",0),
        "failures":failures,
    }
