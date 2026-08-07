from __future__ import annotations

import ast
import hashlib
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "node_modules",
    "dist",
    "build",
    "runtime",
    "output",
    "logs",
    "tmp",
    "temp",
    "bundle",
    "bundles",
    "archive",
    "archives",
}

EXCLUDED_SUFFIXES = {
    ".zip",
    ".joblib",
    ".pkl",
    ".pickle",
    ".dll",
    ".pyd",
    ".exe",
    ".bin",
    ".log",
    ".jsonl",
}

MAX_SCAN_FILE_BYTES = 2 * 1024 * 1024

CATEGORY_PATTERNS = {
    "credentials_profiles": [
        r"credential", r"vault", r"profile", r"configuration",
    ],
    "market_polling": [
        r"market.*poll", r"polling", r"market.*snapshot", r"market.*clock",
    ],
    "signals_strategy": [
        r"signal", r"strategy", r"feature", r"ensemble", r"regime",
    ],
    "risk_approval": [
        r"risk", r"approval", r"guardrail", r"allocation", r"exposure",
    ],
    "order_submission": [
        r"submit.*order", r"order.*submit", r"paper.*execution",
        r"broker.*write", r"micro.*paper",
    ],
    "order_lifecycle": [
        r"order.*lifecycle", r"fill.*recon", r"reconciliation",
        r"cancel.*validation", r"reject.*validation",
    ],
    "positions_portfolio": [
        r"position", r"portfolio", r"trade.*ledger", r"holding",
    ],
    "session_orchestration": [
        r"session.*manager", r"daily.*session", r"orchestr",
        r"automation.*controller", r"autonomous.*paper",
    ],
    "restart_recovery": [
        r"watchdog", r"restart", r"recovery", r"checkpoint", r"lock",
    ],
    "end_of_day": [
        r"end.*of.*day", r"eod", r"daily.*certif", r"session.*report",
    ],
    "monitoring_dashboard": [
        r"monitor", r"dashboard", r"web.*controller", r"health",
        r"notification", r"operations.*manager",
    ],
    "paper_completion": [
        r"paper.*completion", r"long.*run", r"p5", r"actual.*validation",
    ],
}

PREFERRED_HINTS = [
    "actual", "latest", "final", "operations", "controller", "manager",
    "reconciliation", "certification", "validation",
]

DEPRECATED_HINTS = [
    "sample", "example", "fixture", "offline", "sandbox", "old", "backup",
]


@dataclass
class FileRecord:
    path: str
    size_bytes: int
    modified_ns: int
    sha256: str
    categories: list[str]
    functions: list[str]
    classes: list[str]
    safety_flags: dict[str, bool]
    score: int

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "size_bytes": self.size_bytes,
            "modified_ns": self.modified_ns,
            "sha256": self.sha256,
            "categories": self.categories,
            "functions": self.functions,
            "classes": self.classes,
            "safety_flags": self.safety_flags,
            "score": self.score,
        }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return ""


def _python_symbols(text: str) -> tuple[list[str], list[str]]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return [], []
    functions = []
    classes = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append(node.name)
        elif isinstance(node, ast.ClassDef):
            classes.append(node.name)
    return sorted(set(functions)), sorted(set(classes))


def _categories(path_string: str, text: str) -> list[str]:
    haystack = f"{path_string}\n{text[:20000]}".lower()
    matched = []
    for category, patterns in CATEGORY_PATTERNS.items():
        if any(re.search(pattern, haystack) for pattern in patterns):
            matched.append(category)
    return matched


def _safety_flags(text: str) -> dict[str, bool]:
    low = text.lower()
    return {
        "mentions_paper_only": "paper_only" in low or "paper only" in low,
        "mentions_live_off": (
            "live_submission_enabled" in low and "false" in low
        ) or "live submission: off" in low,
        "mentions_broker_write_off": (
            "broker_write_enabled" in low and "false" in low
        ) or "broker write: off" in low,
        "contains_submit_order": "submit_order" in low,
        "contains_cancel_order": "cancel_order" in low,
        "contains_delete_all_positions": "close_all_positions" in low,
    }


def _score(path_string: str, categories: list[str], flags: dict[str, bool]) -> int:
    low = path_string.lower()
    score = len(categories) * 10
    score += sum(4 for hint in PREFERRED_HINTS if hint in low)
    score -= sum(6 for hint in DEPRECATED_HINTS if hint in low)
    if flags["mentions_paper_only"]:
        score += 5
    if flags["mentions_live_off"]:
        score += 5
    if flags["mentions_broker_write_off"]:
        score += 4
    if "/release/" in "/" + low:
        score -= 3
    if low.endswith("_test.py") or "/test_" in "/" + low:
        score -= 4
    return score


class RepositoryScanner:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def iter_files(self) -> Iterable[Path]:
        for path in self.root.rglob("*"):
            if not path.is_file():
                continue

            relative_parts = path.relative_to(self.root).parts

            if any(part.lower() in EXCLUDED_DIRS for part in relative_parts):
                continue

            suffix = path.suffix.lower()

            if suffix in EXCLUDED_SUFFIXES:
                continue

            if suffix not in {
                ".py",
                ".ps1",
                ".json",
                ".md",
                ".txt",
                ".yaml",
                ".yml",
            }:
                continue

            try:
                if path.stat().st_size > MAX_SCAN_FILE_BYTES:
                    continue
            except OSError:
                continue

            yield path

    def scan(self) -> dict:
        records: list[FileRecord] = []
        duplicates: dict[str, list[str]] = defaultdict(list)
        category_map: dict[str, list[dict]] = defaultdict(list)

        for path in self.iter_files():
            relative = path.relative_to(self.root).as_posix()
            text = _text(path)
            categories = _categories(relative, text)
            if not categories:
                continue
            functions, classes = (
                _python_symbols(text) if path.suffix.lower() == ".py"
                else ([], [])
            )
            flags = _safety_flags(text)
            record = FileRecord(
                path=relative,
                size_bytes=path.stat().st_size,
                modified_ns=path.stat().st_mtime_ns,
                sha256=_sha256(path),
                categories=categories,
                functions=functions,
                classes=classes,
                safety_flags=flags,
                score=_score(relative, categories, flags),
            )
            records.append(record)
            duplicates[record.sha256].append(relative)
            for category in categories:
                category_map[category].append(record.to_dict())

        canonical = {}
        for category in CATEGORY_PATTERNS:
            candidates = sorted(
                category_map.get(category, []),
                key=lambda item: (
                    item["score"],
                    item["modified_ns"],
                    -len(item["path"]),
                ),
                reverse=True,
            )
            canonical[category] = {
                "selected": candidates[0] if candidates else None,
                "alternatives": candidates[1:10],
                "candidate_count": len(candidates),
            }

        exact_duplicates = [
            {"sha256": digest, "paths": paths}
            for digest, paths in duplicates.items()
            if len(paths) > 1
        ]

        write_capable = [
            record.to_dict()
            for record in records
            if record.safety_flags["contains_submit_order"]
            or record.safety_flags["contains_cancel_order"]
            or record.safety_flags["contains_delete_all_positions"]
        ]

        required = [
            "credentials_profiles",
            "market_polling",
            "signals_strategy",
            "risk_approval",
            "order_submission",
            "order_lifecycle",
            "positions_portfolio",
            "session_orchestration",
            "restart_recovery",
            "end_of_day",
            "monitoring_dashboard",
            "paper_completion",
        ]
        missing = [
            category for category in required
            if canonical[category]["selected"] is None
        ]

        return {
            "audit_version": "PAPER_TRADING_1_0_PREMARKET_FINALIZATION",
            "repository_root": str(self.root),
            "scanned_relevant_files": len(records),
            "category_count": len(CATEGORY_PATTERNS),
            "missing_categories": missing,
            "canonical": canonical,
            "exact_duplicate_groups": exact_duplicates,
            "write_capable_files": sorted(
                write_capable, key=lambda item: item["path"]
            ),
            "records": [record.to_dict() for record in records],
            "status": "PASS" if not missing else "BLOCKED",
        }


def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
