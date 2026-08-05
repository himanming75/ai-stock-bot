from __future__ import annotations
from pathlib import Path
from typing import Any

from .diagnostics import build_final_diagnostics
from .gates import evaluate_final_release_gate
from .io import write_json
from .release_manifest import build_release_manifest
from .report import build_final_operations_report


def run_bundle_c(root: Path) -> dict[str, Any]:
    actual = (
        root / "release/bundle_c_r14_to_r15_final_operations/actual"
    )
    actual.mkdir(parents=True, exist_ok=True)

    diagnostics = build_final_diagnostics(root)
    write_json(actual / "final_diagnostics.json", diagnostics)

    manifest = build_release_manifest(root)
    write_json(actual / "final_release_manifest.json", manifest)

    gate = evaluate_final_release_gate(root)
    write_json(actual / "final_release_gate.json", gate)

    report = build_final_operations_report(root)
    write_json(actual / "bundle_c_result.json", report)
    return report
