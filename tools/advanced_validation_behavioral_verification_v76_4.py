from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

VERSION = "76.4"
SCHEMA = "v76.4.advanced_validation_behavioral_verification.1"


class VerificationError(ValueError):
    pass


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def validate_config(config: dict[str, Any]) -> None:
    if config.get("verification_scope") != "ADVANCED_VALIDATION_BEHAVIORAL_VERIFICATION":
        raise VerificationError("verification_scope invalid")

    for key in (
        "offline_only",
        "preserve_repository",
        "require_zero_trading_side_effects",
        "require_all_scenarios_pass",
        "require_repeatability",
        "verify_tracked_file_immutability",
    ):
        if config.get(key) is not True:
            raise VerificationError(f"{key} must be true")

    for key in (
        "network_allowed",
        "broker_connection_allowed",
        "order_submission_allowed",
        "repository_mutation_allowed",
        "live_approval_allowed",
    ):
        if config.get(key) is not False:
            raise VerificationError(f"{key} must be false")

    repeat_count = config.get("repeat_count")
    if not isinstance(repeat_count, int) or not 2 <= repeat_count <= 10:
        raise VerificationError("repeat_count must be 2..10")

    scenarios = config.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        raise VerificationError("scenarios must be a non-empty list")

    scenario_ids: set[str] = set()
    for scenario in scenarios:
        if not isinstance(scenario, dict):
            raise VerificationError("scenario must be an object")
        scenario_id = scenario.get("scenario_id")
        if not isinstance(scenario_id, str) or not scenario_id:
            raise VerificationError("scenario_id required")
        if scenario_id in scenario_ids:
            raise VerificationError(f"duplicate scenario_id: {scenario_id}")
        scenario_ids.add(scenario_id)

        script = scenario.get("script")
        if not isinstance(script, str) or not script:
            raise VerificationError("script required")

        timeout = scenario.get("timeout_seconds")
        if not isinstance(timeout, int) or not 1 <= timeout <= 1800:
            raise VerificationError("timeout_seconds must be 1..1800")


def load_config(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise VerificationError(f"config not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise VerificationError(f"invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise VerificationError("config must be an object")
    validate_config(value)
    return value


def safety_environment(repository_root: Path) -> dict[str, str]:
    environment = os.environ.copy()
    repository_value = str(repository_root.resolve())
    existing = environment.get("PYTHONPATH", "")
    environment["PYTHONPATH"] = (
        repository_value
        if not existing
        else repository_value + os.pathsep + existing
    )
    environment.update({
        "AI_STOCK_BOT_NETWORK_ALLOWED": "0",
        "AI_STOCK_BOT_BROKER_ENABLED": "0",
        "AI_STOCK_BOT_ORDER_SUBMISSION_ALLOWED": "0",
        "AI_STOCK_BOT_LIVE_TRADING_ALLOWED": "0",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONHASHSEED": "0",
        "TZ": "UTC",
    })
    return environment


def safe_script(repository_root: Path, relative_value: str) -> Path:
    relative = Path(relative_value)
    if relative.is_absolute() or ".." in relative.parts:
        raise VerificationError(f"unsafe script path: {relative_value}")
    resolved = (repository_root / relative).resolve()
    try:
        resolved.relative_to(repository_root)
    except ValueError as exc:
        raise VerificationError(f"script outside repository: {relative_value}") from exc
    return resolved


def normalize_output(text: str) -> str:
    value = text.replace("\r\n", "\n").replace("\r", "\n")
    value = re.sub(r"Ran \d+ tests? in [0-9.]+s", "Ran <N> tests in <TIME>s", value)
    value = re.sub(r"\b\d+\.\d{3,}s\b", "<TIME>s", value)
    value = re.sub(r"\b\d+\.\d{3,}\b", "<FLOAT>", value)
    value = re.sub(r"[A-Fa-f0-9]{64}", "<SHA256>", value)
    return value.strip()


def tracked_files(repository_root: Path) -> list[Path]:
    completed = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=repository_root,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise VerificationError(
            "git ls-files failed: " +
            completed.stderr.decode("utf-8", "replace")
        )
    names = [
        item.decode("utf-8", "surrogateescape")
        for item in completed.stdout.split(b"\0")
        if item
    ]
    return [repository_root / name for name in names]


def tracked_snapshot(repository_root: Path) -> dict[str, str]:
    snapshot: dict[str, str] = {}
    for path in tracked_files(repository_root):
        relative = path.relative_to(repository_root).as_posix()
        snapshot[relative] = file_sha256(path) if path.is_file() else "<MISSING>"
    return snapshot


def run_once(
    repository_root: Path,
    scenario: dict[str, Any],
    round_number: int,
) -> dict[str, Any]:
    script = safe_script(repository_root, scenario["script"])
    record: dict[str, Any] = {
        "scenario_id": scenario["scenario_id"],
        "round_number": round_number,
        "script": Path(scenario["script"]).as_posix(),
        "exists": script.is_file(),
        "status": "NOT_RUN",
        "return_code": None,
        "timed_out": False,
        "duration_seconds": 0.0,
        "stdout": "",
        "stderr": "",
        "normalized_output_sha256": None,
        "script_sha256": file_sha256(script) if script.is_file() else None,
    }
    if not script.is_file():
        record["status"] = "MISSING"
        record["record_sha256"] = digest(record)
        return record

    command = [sys.executable, str(script)]
    command.extend(str(value) for value in scenario.get("arguments", []))
    started = time.time()
    try:
        completed = subprocess.run(
            command,
            cwd=repository_root,
            env=safety_environment(repository_root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=scenario["timeout_seconds"],
            shell=False,
        )
        record.update({
            "status": "PASS" if completed.returncode == 0 else "FAIL",
            "return_code": completed.returncode,
            "stdout": completed.stdout[-200000:],
            "stderr": completed.stderr[-200000:],
        })
    except subprocess.TimeoutExpired as exc:
        stdout = (
            exc.stdout.decode("utf-8", "replace")
            if isinstance(exc.stdout, bytes)
            else (exc.stdout or "")
        )
        stderr = (
            exc.stderr.decode("utf-8", "replace")
            if isinstance(exc.stderr, bytes)
            else (exc.stderr or "")
        )
        record.update({
            "status": "TIMEOUT",
            "timed_out": True,
            "stdout": stdout[-200000:],
            "stderr": stderr[-200000:],
        })

    record["duration_seconds"] = round(time.time() - started, 6)
    normalized = {
        "return_code": record["return_code"],
        "stdout": normalize_output(record["stdout"]),
        "stderr": normalize_output(record["stderr"]),
    }
    record["normalized_output_sha256"] = digest(normalized)
    record["record_sha256"] = digest({
        key: value for key, value in record.items() if key != "record_sha256"
    })
    return record


def run_verification(repository_root: Path, config: dict[str, Any]) -> dict[str, Any]:
    repository_root = repository_root.resolve()
    if not repository_root.is_dir():
        raise VerificationError(f"repository root not found: {repository_root}")

    started = time.time()
    before = tracked_snapshot(repository_root)
    scenario_results: list[dict[str, Any]] = []

    for scenario in config["scenarios"]:
        rounds = [
            run_once(repository_root, scenario, round_number)
            for round_number in range(1, config["repeat_count"] + 1)
        ]
        output_hashes = [item["normalized_output_sha256"] for item in rounds]
        all_pass = all(item["status"] == "PASS" for item in rounds)
        repeatable = (
            all(value is not None for value in output_hashes)
            and len(set(output_hashes)) == 1
        )
        status = "PASS" if all_pass and repeatable else "FAIL"
        item = {
            "scenario_id": scenario["scenario_id"],
            "name": scenario["name"],
            "status": status,
            "all_rounds_passed": all_pass,
            "repeatable": repeatable,
            "round_count": len(rounds),
            "unique_normalized_output_count": len(set(output_hashes)),
            "rounds": rounds,
            "rounds_sha256": digest(rounds),
        }
        item["scenario_result_sha256"] = digest(item)
        scenario_results.append(item)

    after = tracked_snapshot(repository_root)
    changed_files = sorted(
        name for name in set(before) | set(after)
        if before.get(name) != after.get(name)
    )
    immutable = not changed_files

    passed = sum(item["status"] == "PASS" for item in scenario_results)
    failed = len(scenario_results) - passed
    status = "PASS" if failed == 0 and immutable else "FAIL"

    result = {
        "status": status,
        "decision": (
            "advanced_validation_behavioral_verification_completed"
            if status == "PASS"
            else "advanced_validation_behavioral_verification_failed"
        ),
        "scenario_count": len(scenario_results),
        "passed_scenario_count": passed,
        "failed_scenario_count": failed,
        "failed_scenario_ids": [
            item["scenario_id"] for item in scenario_results
            if item["status"] != "PASS"
        ],
        "repeat_count": config["repeat_count"],
        "total_execution_count": len(scenario_results) * config["repeat_count"],
        "all_outputs_repeatable": all(
            item["repeatable"] for item in scenario_results
        ),
        "tracked_file_immutability_verified": immutable,
        "changed_tracked_files": changed_files,
        "tracked_file_count_before": len(before),
        "tracked_file_count_after": len(after),
        "tracked_snapshot_before_sha256": digest(before),
        "tracked_snapshot_after_sha256": digest(after),
        "scenario_results": scenario_results,
        "scenario_results_sha256": digest(scenario_results),
        "duration_seconds": round(time.time() - started, 6),
        "next_phase": (
            "V76_5_RELEASE_CANDIDATE_SYSTEM_ACCEPTANCE"
            if status == "PASS"
            else "REPAIR_ADVANCED_VALIDATION_GAPS"
        ),
        "orders_submitted": 0,
        "cash_mutations": 0,
        "position_mutations": 0,
        "portfolio_mutations": 0,
        "network_allowed": False,
        "broker_connected": False,
        "approved_for_live": False,
        "schema_version": SCHEMA,
        "version": VERSION,
    }
    result["verification_sha256"] = digest(result)
    return result


def write_outputs(result: dict[str, Any], output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    full_path = output_dir / "advanced_validation_behavioral_verification_v76_4.json"
    summary_path = output_dir / "advanced_validation_behavioral_summary_v76_4.json"

    full_path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    summary = {
        "status": result["status"],
        "scenario_count": result["scenario_count"],
        "passed_scenario_count": result["passed_scenario_count"],
        "failed_scenario_count": result["failed_scenario_count"],
        "failed_scenario_ids": result["failed_scenario_ids"],
        "repeat_count": result["repeat_count"],
        "total_execution_count": result["total_execution_count"],
        "all_outputs_repeatable": result["all_outputs_repeatable"],
        "tracked_file_immutability_verified":
            result["tracked_file_immutability_verified"],
        "changed_tracked_files": result["changed_tracked_files"],
        "next_phase": result["next_phase"],
        "verification_sha256": result["verification_sha256"],
        "scenarios": [{
            "scenario_id": item["scenario_id"],
            "name": item["name"],
            "status": item["status"],
            "all_rounds_passed": item["all_rounds_passed"],
            "repeatable": item["repeatable"],
            "round_count": item["round_count"],
        } for item in result["scenario_results"]],
    }
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return [full_path, summary_path]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--config", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)

    try:
        config = load_config(Path(args.config))
        result = run_verification(Path(args.repository_root), config)
        outputs = write_outputs(result, Path(args.output_dir))
        print(json.dumps({
            "status": result["status"],
            "decision": result["decision"],
            "scenario_count": result["scenario_count"],
            "passed_scenario_count": result["passed_scenario_count"],
            "failed_scenario_count": result["failed_scenario_count"],
            "failed_scenario_ids": result["failed_scenario_ids"],
            "repeat_count": result["repeat_count"],
            "total_execution_count": result["total_execution_count"],
            "all_outputs_repeatable": result["all_outputs_repeatable"],
            "tracked_file_immutability_verified":
                result["tracked_file_immutability_verified"],
            "changed_tracked_files": result["changed_tracked_files"],
            "next_phase": result["next_phase"],
            "orders_submitted": result["orders_submitted"],
            "network_allowed": result["network_allowed"],
            "approved_for_live": result["approved_for_live"],
            "outputs": [str(path) for path in outputs],
            "verification_sha256": result["verification_sha256"],
        }, indent=2, sort_keys=True))
        return 0 if result["status"] == "PASS" else 1
    except (VerificationError, OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({
            "status": "FAIL",
            "decision": "advanced_validation_behavioral_verification_failed",
            "error": str(exc),
            "orders_submitted": 0,
            "network_allowed": False,
            "broker_connected": False,
            "approved_for_live": False,
            "version": VERSION,
        }, indent=2, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
