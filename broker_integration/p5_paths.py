from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class P5Paths:
    root: Path

    @property
    def actual_root(self) -> Path:
        return self.root / "release/p5_paper_long_run_qualification/actual"

    @property
    def checkpoint(self) -> Path:
        return self.actual_root / "qualification_checkpoint.json"

    @property
    def result(self) -> Path:
        return self.actual_root / "p5_qualification_result.json"

    @property
    def cycle_ledger(self) -> Path:
        return self.actual_root / "qualification_cycle_ledger.jsonl"
