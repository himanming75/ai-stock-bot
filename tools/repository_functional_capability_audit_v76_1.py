from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

VERSION = "76.1"
SCHEMA = "v76.1.repository_functional_capability_audit.1"


class RepositoryAuditError(ValueError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_of(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def read_text_auto(path: Path) -> str:
    data = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-16", "utf-16-le", "cp1252"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise RepositoryAuditError(f"unsupported text encoding: {path}")


def normalize_path(value: str) -> str:
    value = value.strip().replace("\\", "/")
    while value.startswith("./"):
        value = value[2:]
    return value


def read_path_list(path: Path) -> List[str]:
    try:
        text = read_text_auto(path)
    except FileNotFoundError as exc:
        raise RepositoryAuditError(f"file not found: {path}") from exc

    result: List[str] = []
    seen: Set[str] = set()
    for raw in text.splitlines():
        item = normalize_path(raw)
        if not item or item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def read_json(path: Path) -> Dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RepositoryAuditError(f"file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RepositoryAuditError(f"invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise RepositoryAuditError("top-level config must be an object")
    return value


def matches(path: str, patterns: Sequence[str]) -> bool:
    path_lower = path.lower()
    return any(fnmatch.fnmatch(path_lower, pattern.lower()) for pattern in patterns)


def matched_paths(paths: Iterable[str], patterns: Sequence[str]) -> List[str]:
    return sorted(path for path in paths if matches(path, patterns))


def validate_config(config: Dict[str, Any]) -> None:
    if config.get("audit_scope") != "REPOSITORY_FUNCTIONAL_CAPABILITY_AUDIT":
        raise RepositoryAuditError("audit_scope invalid")

    for key in (
        "offline_only",
        "filename_evidence_only",
        "preserve_repository",
        "require_tracked_file_evidence",
        "require_test_evidence",
        "require_release_evidence",
        "require_conservative_classification",
        "require_zero_trading_side_effects",
    ):
        if config.get(key) is not True:
            raise RepositoryAuditError(f"{key} must be true")

    for key in (
        "network_allowed",
        "broker_connection_allowed",
        "order_submission_allowed",
        "repository_mutation_allowed",
        "live_approval_allowed",
    ):
        if config.get(key) is not False:
            raise RepositoryAuditError(f"{key} must be false")

    capabilities = config.get("capabilities")
    if not isinstance(capabilities, list) or not capabilities:
        raise RepositoryAuditError("capabilities must be a non-empty list")

    seen: Set[str] = set()
    for capability in capabilities:
        if not isinstance(capability, dict):
            raise RepositoryAuditError("capability definition must be an object")
        capability_id = capability.get("capability_id")
        if not isinstance(capability_id, str) or not capability_id:
            raise RepositoryAuditError("capability_id required")
        if capability_id in seen:
            raise RepositoryAuditError(f"duplicate capability_id: {capability_id}")
        seen.add(capability_id)
        evidence_rules = capability.get("evidence_rules")
        if not isinstance(evidence_rules, dict):
            raise RepositoryAuditError(f"evidence_rules required for {capability_id}")
        for category in ("implementation", "tests", "release"):
            patterns = evidence_rules.get(category)
            if not isinstance(patterns, list) or not patterns:
                raise RepositoryAuditError(
                    f"{category} patterns required for {capability_id}"
                )


def classify(
    implementation: List[str],
    tests: List[str],
    release: List[str],
    local_only: List[str],
) -> Tuple[str, str, List[str]]:
    gates = {
        "implementation": bool(implementation),
        "tests": bool(tests),
        "release": bool(release),
    }
    missing = [key for key, passed in gates.items() if not passed]

    if all(gates.values()):
        return (
            "COMPLETE",
            "FILENAME_EVIDENCE_COMPLETE",
            ["Run targeted behavioral tests before stable-release acceptance."],
        )

    if implementation and tests:
        return (
            "PARTIAL",
            "IMPLEMENTATION_AND_TEST_EVIDENCE_WITHOUT_RELEASE_EVIDENCE",
            ["Create or identify release/audit evidence.", "Run targeted tests."],
        )

    if implementation or tests or release or local_only:
        actions: List[str] = []
        if not implementation:
            actions.append("Locate or implement production code.")
        if not tests:
            actions.append("Add or locate targeted tests.")
        if not release:
            actions.append("Add or locate release/audit evidence.")
        if local_only:
            actions.append("Review local-only evidence before adding it to Git.")
        return "PARTIAL", "INCOMPLETE_FILENAME_EVIDENCE", actions

    return (
        "MISSING",
        "NO_MATCHING_FILENAME_EVIDENCE",
        [
            "Confirm whether capability exists under unexpected naming.",
            "Implement capability only if repository review confirms it is absent.",
        ],
    )


def audit_repository(
    tracked_paths: Sequence[str],
    all_paths: Sequence[str],
    config: Dict[str, Any],
) -> Dict[str, Any]:
    validate_config(config)

    tracked = sorted(set(normalize_path(p) for p in tracked_paths if normalize_path(p)))
    all_files = sorted(set(normalize_path(p) for p in all_paths if normalize_path(p)))
    tracked_set = set(tracked)
    all_set = set(all_files)
    local_only_set = all_set - tracked_set
    missing_on_disk_set = tracked_set - all_set

    capabilities: List[Dict[str, Any]] = []
    counts = {"COMPLETE": 0, "PARTIAL": 0, "MISSING": 0, "BLOCKED": 0}

    for sequence, definition in enumerate(config["capabilities"], 1):
        rules = definition["evidence_rules"]
        implementation = matched_paths(tracked, rules["implementation"])
        tests = matched_paths(tracked, rules["tests"])
        release = matched_paths(tracked, rules["release"])

        all_patterns = (
            list(rules["implementation"])
            + list(rules["tests"])
            + list(rules["release"])
        )
        local_only = matched_paths(local_only_set, all_patterns)

        state, evidence_level, actions = classify(
            implementation, tests, release, local_only
        )
        counts[state] += 1

        evidence = {
            "implementation": implementation,
            "tests": tests,
            "release": release,
            "local_only": local_only,
        }

        capabilities.append({
            "sequence": sequence,
            "capability_id": definition["capability_id"],
            "name": definition["name"],
            "category": definition["category"],
            "state": state,
            "evidence_level": evidence_level,
            "filename_evidence_only": True,
            "behavior_verified": False,
            "implementation_evidence_count": len(implementation),
            "test_evidence_count": len(tests),
            "release_evidence_count": len(release),
            "local_only_evidence_count": len(local_only),
            "evidence": evidence,
            "evidence_sha256": sha256_of(evidence),
            "recommended_actions": actions,
        })

    priority = {"MISSING": 0, "BLOCKED": 1, "PARTIAL": 2, "COMPLETE": 3}
    gap_plan = [
        {
            "capability_id": item["capability_id"],
            "name": item["name"],
            "state": item["state"],
            "evidence_level": item["evidence_level"],
            "recommended_actions": item["recommended_actions"],
        }
        for item in capabilities
        if item["state"] != "COMPLETE"
    ]
    gap_plan.sort(
        key=lambda item: (
            priority[item["state"]],
            next(
                row["sequence"]
                for row in capabilities
                if row["capability_id"] == item["capability_id"]
            ),
        )
    )
    for index, item in enumerate(gap_plan, 1):
        item["priority"] = index

    tracked_hash = sha256_of(tracked)
    all_hash = sha256_of(all_files)
    audit_id = "RFCA-" + hashlib.sha256(
        f"{tracked_hash}|{all_hash}|{VERSION}".encode("utf-8")
    ).hexdigest()[:16].upper()

    result: Dict[str, Any] = {
        "status": "PASS",
        "decision": "repository_functional_capability_audit_completed",
        "audit_id": audit_id,
        "audit_method": "FILENAME_EVIDENCE_ONLY",
        "behavioral_completion_claimed": False,
        "tracked_file_count": len(tracked),
        "all_local_file_count": len(all_files),
        "local_only_file_count": len(local_only_set),
        "tracked_missing_on_disk_count": len(missing_on_disk_set),
        "tracked_paths_sha256": tracked_hash,
        "all_paths_sha256": all_hash,
        "local_only_paths": sorted(local_only_set),
        "missing_on_disk_paths": sorted(missing_on_disk_set),
        "capability_count": len(capabilities),
        "complete_count": counts["COMPLETE"],
        "partial_count": counts["PARTIAL"],
        "missing_count": counts["MISSING"],
        "blocked_count": counts["BLOCKED"],
        "capabilities": capabilities,
        "capabilities_sha256": sha256_of(capabilities),
        "functional_gap_plan": gap_plan,
        "functional_gap_plan_sha256": sha256_of(gap_plan),
        "next_phase": (
            "TARGETED_BEHAVIORAL_CAPABILITY_VERIFICATION"
            if counts["MISSING"] == 0
            else "VERIFY_OR_IMPLEMENT_MISSING_CAPABILITY"
        ),
        "next_recommended_capability": (
            None if not gap_plan else gap_plan[0]["capability_id"]
        ),
        "orders_submitted": 0,
        "settlements_created": 0,
        "cash_mutations": 0,
        "position_mutations": 0,
        "portfolio_mutations": 0,
        "repository_mutations": 0,
        "network_used": False,
        "broker_connected": False,
        "approved_for_live": False,
        "schema_version": SCHEMA,
        "version": VERSION,
    }
    result["audit_sha256"] = sha256_of(result)
    return result


def write_outputs(result: Dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    payloads = {
        "repository_functional_capability_audit_v76_1.json": result,
        "repository_functional_capability_inventory_v76_1.json": {
            "audit_id": result["audit_id"],
            "capabilities": result["capabilities"],
            "capabilities_sha256": result["capabilities_sha256"],
        },
        "repository_functional_gap_plan_v76_1.json": {
            "audit_id": result["audit_id"],
            "functional_gap_plan": result["functional_gap_plan"],
            "functional_gap_plan_sha256": result["functional_gap_plan_sha256"],
        },
        "repository_local_only_files_v76_1.json": {
            "audit_id": result["audit_id"],
            "local_only_file_count": result["local_only_file_count"],
            "local_only_paths": result["local_only_paths"],
        },
    }
    for filename, payload in payloads.items():
        (output_dir / filename).write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tracked-files", required=True)
    parser.add_argument("--all-files", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)

    try:
        result = audit_repository(
            read_path_list(Path(args.tracked_files)),
            read_path_list(Path(args.all_files)),
            read_json(Path(args.config)),
        )
        write_outputs(result, Path(args.output_dir))
        summary_keys = (
            "status",
            "decision",
            "audit_id",
            "audit_method",
            "tracked_file_count",
            "all_local_file_count",
            "local_only_file_count",
            "tracked_missing_on_disk_count",
            "capability_count",
            "complete_count",
            "partial_count",
            "missing_count",
            "next_phase",
            "next_recommended_capability",
            "orders_submitted",
            "network_used",
            "approved_for_live",
            "audit_sha256",
        )
        print(json.dumps(
            {key: result[key] for key in summary_keys},
            indent=2,
            sort_keys=True,
        ))
        return 0
    except (RepositoryAuditError, OSError, KeyError, TypeError, ValueError) as exc:
        print(json.dumps({
            "status": "FAIL",
            "decision": "repository_functional_capability_audit_failed",
            "error": str(exc),
            "orders_submitted": 0,
            "repository_mutations": 0,
            "network_used": False,
            "broker_connected": False,
            "approved_for_live": False,
            "version": VERSION,
        }, indent=2, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
