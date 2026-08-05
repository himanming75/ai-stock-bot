
from __future__ import annotations
from pathlib import Path
from typing import Any
import hashlib, json, re

from .catalog import FEATURE_CATALOG

TEXT_SUFFIXES = {".py", ".ps1", ".json", ".md", ".txt", ".yml", ".yaml", ".toml", ".ini"}
IGNORED_PARTS = {".git", ".venv", "__pycache__", "node_modules"}
SELF_EXCLUDED_PREFIXES = (
    "paper_broker_audit/",
    "tools/run_v451_to_v460_audit.py",
    "tools/test_v451_to_v460_audit.py",
    "tools/verify_v451_to_v460_audit.py",
    "release/v451_01/",
    "release/v460_64/",
    "V451_TO_V460_MANIFEST.json",
    "GIT_COMMIT_V451_TO_V460.txt",
)

def _hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

def _files(root: Path):
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if any(part in IGNORED_PARTS for part in path.parts):
            continue
        yield path

def run_audit(root: Path) -> dict[str, Any]:
    indexed = []
    combined = {}
    for path in _files(root):
        rel = path.relative_to(root).as_posix()
        if rel.startswith(SELF_EXCLUDED_PREFIXES):
            continue
        try:
            text = path.read_text(encoding="utf-8-sig", errors="ignore")
        except OSError:
            continue
        lower = text.lower()
        combined[rel] = lower
        indexed.append(rel)

    features = {}
    for name, spec in FEATURE_CATALOG.items():
        evidence = []
        matched_patterns = set()
        for rel, text in combined.items():
            local_matches = [p for p in spec["patterns"] if p.lower() in text]
            if local_matches:
                evidence.append({"path": rel, "patterns": sorted(local_matches)})
                matched_patterns.update(local_matches)

        ratio = len(matched_patterns) / max(1, len(spec["patterns"]))
        if ratio >= 0.67 and len(evidence) >= 1:
            status = "IMPLEMENTED_CANDIDATE"
        elif evidence:
            status = "PARTIAL_OR_INDIRECT"
        else:
            status = "NOT_FOUND"

        features[name] = {
            "required": spec["required"],
            "status": status,
            "matched_pattern_count": len(matched_patterns),
            "pattern_count": len(spec["patterns"]),
            "evidence": evidence[:20],
        }

    counts = {
        "implemented_candidate": sum(v["status"] == "IMPLEMENTED_CANDIDATE" for v in features.values()),
        "partial_or_indirect": sum(v["status"] == "PARTIAL_OR_INDIRECT" for v in features.values()),
        "not_found": sum(v["status"] == "NOT_FOUND" for v in features.values()),
        "total": len(features),
    }
    missing = [k for k, v in features.items() if v["status"] == "NOT_FOUND"]
    partial = [k for k, v in features.items() if v["status"] == "PARTIAL_OR_INDIRECT"]

    report_core = {
        "audit_version": "V460.64",
        "repository_root": str(root),
        "files_indexed": len(indexed),
        "counts": counts,
        "features": features,
        "missing_features": missing,
        "partial_features": partial,
    }
    report_core["audit_hash"] = _hash(report_core)
    report_core["next_bundle_scope"] = {
        "reuse_candidates": [k for k, v in features.items() if v["status"] == "IMPLEMENTED_CANDIDATE"],
        "must_complete": sorted(set(missing + partial)),
        "mandatory_features_omitted": [],
    }
    return report_core
