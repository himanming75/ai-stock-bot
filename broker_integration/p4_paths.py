from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class P4Paths:
    root: Path

    @property
    def actual_root(self) -> Path:
        return self.root / "release/p4_autonomous_paper_runtime/actual"

    @property
    def lock(self) -> Path:
        return self.actual_root / "runtime.lock.json"

    @property
    def heartbeat(self) -> Path:
        return self.actual_root / "heartbeat.json"

    @property
    def cycle_registry(self) -> Path:
        return self.actual_root / "cycle_registry.json"

    @property
    def cycle_ledger(self) -> Path:
        return self.actual_root / "cycle_ledger.jsonl"

    @property
    def checkpoint(self) -> Path:
        return self.actual_root / "runtime_checkpoint.json"

    @property
    def latest_result(self) -> Path:
        return self.actual_root / "p4_runtime_result.json"

    def as_mapping(self) -> dict[str, Path]:
        return {
            "lock": self.lock,
            "heartbeat": self.heartbeat,
            "cycle_registry": self.cycle_registry,
            "cycle_ledger": self.cycle_ledger,
            "checkpoint": self.checkpoint,
        }
