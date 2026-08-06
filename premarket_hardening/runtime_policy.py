from __future__ import annotations
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RuntimeRule:
    pattern: str
    category: str
    retention_days: int
    compress_after_days: int
    protected: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


RULES = (
    RuntimeRule(
        "release/**/actual/cycle_*",
        "POLLING_CYCLE",
        7,
        1,
    ),
    RuntimeRule(
        "release/**/actual/*.jsonl",
        "LEDGER",
        30,
        7,
    ),
    RuntimeRule(
        "release/**/actual/*state*.json",
        "RUNTIME_STATE",
        14,
        7,
    ),
    RuntimeRule(
        "release/**/actual/*checkpoint*.json",
        "CHECKPOINT",
        14,
        7,
        protected=True,
    ),
    RuntimeRule(
        "release/**/actual/*.log",
        "RUNTIME_LOG",
        14,
        3,
    ),
)


def classify_path(path: str) -> dict:
    value = path.replace("\\", "/")
    if "/actual/cycle_" in value:
        return {"category": "POLLING_CYCLE", "runtime": True}
    if value.endswith(".jsonl") and "/actual/" in value:
        return {"category": "LEDGER", "runtime": True}
    if (
        "/actual/" in value
        and value.endswith(".json")
        and any(
            token in value.lower()
            for token in (
                "state",
                "summary",
                "snapshot",
                "checkpoint",
                "result",
                "token",
            )
        )
    ):
        return {"category": "RUNTIME_JSON", "runtime": True}
    if value.endswith(".log"):
        return {"category": "RUNTIME_LOG", "runtime": True}
    return {"category": "SOURCE_OR_RELEASE", "runtime": False}


def gitignore_append_block() -> str:
    return """
# V6801-V7000 generated runtime outputs
release/**/actual/cycle_*/
release/**/actual/*.log
release/**/actual/*_state.json
release/**/actual/*_summary.json
release/**/actual/*_snapshot.json
release/**/actual/*_token.json
release/**/actual/*_result.json
release/**/actual/*.runtime.json
release/**/actual/*.runtime.jsonl
runtime/
.runtime/
*.runtime.log
*.runtime.json
*.runtime.jsonl
"""
