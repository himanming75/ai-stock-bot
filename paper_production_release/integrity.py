from __future__ import annotations

from pathlib import Path
from typing import Any

from paper_production_release.io import sha256_file


REQUIRED_FILES = [
    "paper_orchestrator/engine.py",
    "paper_orchestrator/steps.py",
    "web_ui_v2/app.py",
    "release/v88_09_to_v88_16/actual/paper_orchestrator_result.json",
    "release/v87_09_to_v87_16/actual/walk_forward_stress_validation_result.json",
    "release/v87_17_to_v87_24/actual/multi_asset_backtest_result.json",
    "release/v88_01_to_v88_08/actual/web_ui_v2_state.json",
]


def build_integrity_manifest(root: Path) -> dict[str, Any]:
    files = []
    missing = []
    for relative in REQUIRED_FILES:
        path = root / relative
        if not path.exists():
            missing.append(relative)
            continue
        files.append({
            "path": relative,
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        })

    return {
        "required_file_count": len(REQUIRED_FILES),
        "verified_file_count": len(files),
        "missing_files": missing,
        "files": files,
        "integrity_passed": not missing,
    }
