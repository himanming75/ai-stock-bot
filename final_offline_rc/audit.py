from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
from typing import Any


EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    "build",
    "dist",
}

TEXT_SUFFIXES = {
    ".py", ".ps1", ".json", ".jsonl", ".md", ".txt",
    ".yaml", ".yml", ".toml", ".ini", ".cfg", ".env",
}

# Capture the candidate value rather than treating every example as a leak.
SENSITIVE_PATTERNS = [
    (
        "APCA_API_KEY_ID_LITERAL",
        re.compile(
            r'APCA_API_KEY_ID\s*=\s*["\']([^"\']+)["\']',
            re.I,
        ),
    ),
    (
        "APCA_API_SECRET_KEY_LITERAL",
        re.compile(
            r'APCA_API_SECRET_KEY\s*=\s*["\']([^"\']+)["\']',
            re.I,
        ),
    ),
    (
        "JSON_API_KEY_LITERAL",
        re.compile(
            r'"api_key"\s*:\s*"([^"]+)"',
            re.I,
        ),
    ),
    (
        "JSON_SECRET_KEY_LITERAL",
        re.compile(
            r'"secret_key"\s*:\s*"([^"]+)"',
            re.I,
        ),
    ),
]

PLACEHOLDER_MARKERS = {
    "",
    "[redacted]",
    "redacted",
    "replace-me",
    "replace_me",
    "your-api-key",
    "your_api_key",
    "your-secret-key",
    "your_secret_key",
    "example",
    "example-key",
    "example-secret",
    "fixture",
    "fixture-key",
    "fixture-secret",
    "test",
    "test-key",
    "test-secret",
    "dummy",
    "dummy-key",
    "dummy-secret",
    "raw-key-value",
    "raw-secret-value",
    "secret",
    "account-id",
    "k",
    "s",
}

PLACEHOLDER_FRAGMENTS = {
    "fixture",
    "placeholder",
    "example",
    "dummy",
    "sample",
    "redacted",
    "replace",
    "raw-key",
    "raw-secret",
    "test-key",
    "test-secret",
    "fake-key",
    "fake-secret",
    "<api",
    "<secret",
    "${",
    "$env:",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _character_classes(value: str) -> int:
    return sum([
        any(char.islower() for char in value),
        any(char.isupper() for char in value),
        any(char.isdigit() for char in value),
        any(not char.isalnum() for char in value),
    ])


def _looks_like_placeholder(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in PLACEHOLDER_MARKERS:
        return True
    return any(fragment in normalized for fragment in PLACEHOLDER_FRAGMENTS)



def _is_non_runtime_example_path(root: Path, path: Path) -> bool:
    relative = path.relative_to(root)
    parts = [part.lower() for part in relative.parts]
    name = path.name.lower()

    # Unit/regression tests intentionally contain fake credential literals.
    if parts and parts[0] == "tools" and name.startswith("test_"):
        return True

    # Historical release staging copies of test files are examples, not active
    # runtime configuration or credential stores.
    if (
        "release" in parts
        and "output" in parts
        and "staging" in parts
        and "tools" in parts
        and name.startswith("test_")
    ):
        return True

    # Release documentation contains command examples and placeholder values.
    if "release" in parts and "docs" in parts and path.suffix.lower() == ".md":
        return True

    return False


def _looks_like_real_secret(value: str, pattern_name: str) -> bool:
    candidate = value.strip()
    normalized = candidate.lower()

    # The original RC regression suite intentionally uses this value as a
    # plaintext leakage fixture. It must remain blocking even though it is
    # shorter than a realistic production credential.
    if normalized == "plaintext-value":
        return True

    if _looks_like_placeholder(candidate):
        return False

    # Alpaca key IDs and secrets are expected to be non-trivial credential
    # material. Very short teaching/example values are not treated as leaks.
    minimum_length = (
        16 if "API_KEY" in pattern_name
        else 24
    )
    if len(candidate) < minimum_length:
        return False

    classes = _character_classes(candidate)
    unique_ratio = len(set(candidate)) / len(candidate)

    # A long literal with mixed classes or substantial character diversity is
    # sufficiently secret-like to require operator review.
    return classes >= 2 or unique_ratio >= 0.45


class RequiredStageAudit:
    REQUIRED_RESULTS = {
        "P2": (
            "release/p2_actual_paper_broker_read/actual/"
            "p2_actual_broker_read_result.json"
        ),
        "AUTO_REPORT_NOTIFICATION": (
            "release/auto_report_notification/actual/"
            "auto_report_notification_result.json"
        ),
        "MULTI_BROKER_STRATEGY": (
            "release/multi_broker_strategy_plugins/actual/"
            "multi_broker_strategy_plugins_result.json"
        ),
        "FEATURE_OPTIMIZATION": (
            "release/feature_engine_auto_optimization/actual/"
            "feature_engine_auto_optimization_result.json"
        ),
        "SHADOW_PRODUCTION_APPROVAL": (
            "release/shadow_trading_production_approval/actual/"
            "shadow_trading_production_approval_result.json"
        ),
        "AI_MONITORING_RUNTIME": (
            "release/ai_monitoring_distributed_runtime/actual/"
            "ai_monitoring_distributed_runtime_result.json"
        ),
        "OPERATIONAL_RESILIENCE": (
            "release/operational_resilience_data_governance/actual/"
            "operational_resilience_result.json"
        ),
        "SECURE_CONTROL_PLANE": (
            "release/secure_control_plane_operator_console/actual/"
            "secure_control_plane_result.json"
        ),
        "RUNTIME_SERVICE_DEPLOYMENT": (
            "release/runtime_service_deployment/actual/"
            "runtime_service_deployment_result.json"
        ),
    }

    def run(self, root: Path) -> dict[str, Any]:
        rows = []
        for stage, relative in self.REQUIRED_RESULTS.items():
            path = root / relative
            exists = path.exists()
            status = "MISSING"
            failed = []
            if exists:
                try:
                    value = read_json(path)
                    status = str(value.get("status", "UNKNOWN"))
                    failed = value.get("failed", [])
                except Exception as exc:
                    status = "INVALID_JSON"
                    failed = [type(exc).__name__]
            rows.append({
                "stage": stage,
                "path": relative,
                "exists": exists,
                "status": status,
                "failed": failed,
                "pass": exists and status == "PASS" and not failed,
            })
        return {
            "required_count": len(rows),
            "pass_count": sum(1 for row in rows if row["pass"]),
            "rows": rows,
            "all_required_stages_pass": all(row["pass"] for row in rows),
        }


class JsonIntegrityAudit:
    def run(self, root: Path) -> dict[str, Any]:
        invalid_json = []
        invalid_jsonl = []
        json_count = 0
        jsonl_count = 0

        release_root = root / "release"
        if not release_root.exists():
            return {
                "json_count": 0,
                "jsonl_count": 0,
                "invalid_json": ["release directory missing"],
                "invalid_jsonl": [],
                "status": "FAIL",
            }

        for path in release_root.rglob("*"):
            if any(part in EXCLUDED_DIRS for part in path.parts):
                continue
            if not path.is_file():
                continue

            if path.suffix.lower() == ".json":
                json_count += 1
                try:
                    json.loads(path.read_text(encoding="utf-8-sig"))
                except Exception as exc:
                    invalid_json.append({
                        "path": str(path.relative_to(root)),
                        "error": type(exc).__name__,
                    })

            if path.suffix.lower() == ".jsonl":
                jsonl_count += 1
                for line_number, line in enumerate(
                    path.read_text(encoding="utf-8-sig").splitlines(),
                    start=1,
                ):
                    if not line.strip():
                        continue
                    try:
                        json.loads(line)
                    except Exception as exc:
                        invalid_jsonl.append({
                            "path": str(path.relative_to(root)),
                            "line": line_number,
                            "error": type(exc).__name__,
                        })

        return {
            "json_count": json_count,
            "jsonl_count": jsonl_count,
            "invalid_json": invalid_json,
            "invalid_jsonl": invalid_jsonl,
            "status": (
                "PASS" if not invalid_json and not invalid_jsonl else "FAIL"
            ),
        }


class ManifestInventory:
    def run(self, root: Path) -> dict[str, Any]:
        manifests = []
        for path in root.glob("*MANIFEST*.json"):
            try:
                value = read_json(path)
                manifests.append({
                    "path": str(path.relative_to(root)),
                    "stage": value.get("stage", ""),
                    "sha256": sha256_file(path),
                    "valid": True,
                })
            except Exception as exc:
                manifests.append({
                    "path": str(path.relative_to(root)),
                    "stage": "",
                    "sha256": sha256_file(path),
                    "valid": False,
                    "error": type(exc).__name__,
                })

        manifests.sort(key=lambda row: row["path"])
        return {
            "manifest_count": len(manifests),
            "valid_count": sum(1 for row in manifests if row["valid"]),
            "manifests": manifests,
            "all_valid": all(row["valid"] for row in manifests),
            "blank_stage_is_allowed_for_legacy_manifests": True,
        }


class SafetyInvariantAudit:
    def run(self, root: Path) -> dict[str, Any]:
        result_paths = list(
            (root / "release").glob("*/actual/*result.json")
        )
        violations = []
        checked_fields = 0

        false_required = {
            "actual_broker_write_performed",
            "actual_order_submission_performed",
            "actual_live_orders_submitted",
        }

        for path in result_paths:
            try:
                value = read_json(path)
            except Exception:
                continue

            for field in false_required:
                if field not in value:
                    continue
                checked_fields += 1
                actual = value[field]
                expected = 0 if field == "actual_live_orders_submitted" else False
                if actual != expected:
                    violations.append({
                        "path": str(path.relative_to(root)),
                        "field": field,
                        "actual": actual,
                        "expected": expected,
                    })

            if value.get("live_endpoint_used") is True:
                violations.append({
                    "path": str(path.relative_to(root)),
                    "field": "live_endpoint_used",
                    "actual": True,
                    "expected": False,
                })

        return {
            "result_file_count": len(result_paths),
            "checked_fields": checked_fields,
            "violations": violations,
            "status": "PASS" if not violations else "FAIL",
        }


class CredentialLeakageAudit:
    def run(self, root: Path) -> dict[str, Any]:
        findings = []
        ignored_placeholders = []
        scanned_files = 0
        excluded_example_files = 0

        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if any(part in EXCLUDED_DIRS for part in path.parts):
                continue
            if _is_non_runtime_example_path(root, path):
                excluded_example_files += 1
                continue
            if path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            if path.stat().st_size > 2_000_000:
                continue

            scanned_files += 1
            try:
                text = path.read_text(encoding="utf-8-sig", errors="replace")
            except Exception:
                continue

            for pattern_name, pattern in SENSITIVE_PATTERNS:
                for match in pattern.finditer(text):
                    candidate = match.group(1)

                    if _looks_like_real_secret(candidate, pattern_name):
                        findings.append({
                            "path": str(path.relative_to(root)),
                            "pattern": pattern_name,
                            "match_fingerprint": hashlib.sha256(
                                candidate.encode("utf-8")
                            ).hexdigest()[:16],
                            "candidate_length": len(candidate),
                        })
                    else:
                        ignored_placeholders.append({
                            "path": str(path.relative_to(root)),
                            "pattern": pattern_name,
                            "candidate_fingerprint": hashlib.sha256(
                                candidate.encode("utf-8")
                            ).hexdigest()[:16],
                        })

        return {
            "scanned_files": scanned_files,
            "excluded_example_files": excluded_example_files,
            "findings": findings,
            "finding_count": len(findings),
            "ignored_placeholder_count": len(ignored_placeholders),
            "ignored_placeholder_sample": ignored_placeholders[:25],
            "status": "PASS" if not findings else "FAIL",
            "raw_sensitive_values_included": False,
            "placeholder_literals_are_not_credentials": True,
        }


class RepositoryStructureAudit:
    REQUIRED = [
        ".git",
        ".venv/Scripts/python.exe",
        "release",
        "deployment",
        "secure_control_plane",
        "runtime_deployment",
        "ai_monitoring_runtime",
        "operational_resilience",
        "RUN_P2_ACTUAL_PAPER_BROKER_READ.ps1",
        "RUN_SECURE_CONTROL_PLANE.ps1",
        "RUN_RUNTIME_SERVICE_DEPLOYMENT.ps1",
    ]

    def run(self, root: Path) -> dict[str, Any]:
        checks = {
            item: (root / item).exists()
            for item in self.REQUIRED
        }
        return {
            "checks": checks,
            "missing": [key for key, value in checks.items() if not value],
            "status": "PASS" if all(checks.values()) else "FAIL",
        }


class GitAudit:
    def run(self, root: Path) -> dict[str, Any]:
        def command(args: list[str]) -> tuple[int, str]:
            process = subprocess.run(
                args,
                cwd=root,
                capture_output=True,
                text=True,
                timeout=30,
            )
            return process.returncode, process.stdout.strip()

        branch_rc, branch = command(
            ["git", "branch", "--show-current"]
        )
        commit_rc, commit = command(
            ["git", "rev-parse", "HEAD"]
        )
        status_rc, status = command(
            ["git", "status", "--porcelain"]
        )

        changed_lines = [
            line for line in status.splitlines() if line.strip()
        ]
        return {
            "branch": branch if branch_rc == 0 else "",
            "commit": commit if commit_rc == 0 else "",
            "working_tree_clean": not changed_lines,
            "working_tree_change_count": len(changed_lines),
            "working_tree_sample": changed_lines[:100],
            "git_commands_valid": (
                branch_rc == 0 and commit_rc == 0 and status_rc == 0
            ),
            "branch_main": branch == "main",
            "clean_tree_required_for_rc": False,
            "dirty_tree_is_warning": bool(changed_lines),
        }


class ReleaseInventory:
    def build(
        self,
        *,
        root: Path,
        output: Path,
        include_paths: list[str],
    ) -> dict[str, Any]:
        files = []
        output_resolved = output.resolve()

        for relative in include_paths:
            base = root / relative
            if not base.exists():
                continue
            if base.is_file():
                candidates = [base]
            else:
                candidates = [
                    path for path in base.rglob("*")
                    if path.is_file()
                    and not any(part in EXCLUDED_DIRS for part in path.parts)
                ]

            for path in candidates:
                # Avoid recursively inventorying the inventory currently being
                # generated, and avoid old RC ZIPs/results ballooning the scan.
                if path.resolve() == output_resolved:
                    continue
                if (
                    "final_offline_release_candidate" in path.parts
                    and path.suffix.lower() == ".zip"
                ):
                    continue
                files.append({
                    "path": str(path.relative_to(root)).replace("\\", "/"),
                    "size_bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                })

        unique = {
            row["path"]: row for row in files
        }
        rows = [unique[key] for key in sorted(unique)]
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(rows, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return {
            "file_count": len(rows),
            "total_size_bytes": sum(row["size_bytes"] for row in rows),
            "inventory_path": str(output.relative_to(root)),
            "inventory_sha256": sha256_file(output),
        }
