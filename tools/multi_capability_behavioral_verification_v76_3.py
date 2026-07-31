from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

VERSION = "76.3A"
SCHEMA = "v76.3.multi_capability_behavioral_verification.1"


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
    if config.get("verification_scope") != "MULTI_CAPABILITY_BEHAVIORAL_VERIFICATION":
        raise VerificationError("verification_scope invalid")

    for key in (
        "offline_only",
        "preserve_repository",
        "require_zero_trading_side_effects",
        "require_all_capabilities_pass",
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

    capabilities = config.get("capabilities")
    if not isinstance(capabilities, list) or not capabilities:
        raise VerificationError("capabilities must be a non-empty list")

    capability_ids: set[str] = set()
    verification_ids: set[str] = set()
    for capability in capabilities:
        if not isinstance(capability, dict):
            raise VerificationError("capability must be an object")
        capability_id = capability.get("capability_id")
        if not isinstance(capability_id, str) or not capability_id:
            raise VerificationError("capability_id required")
        if capability_id in capability_ids:
            raise VerificationError(f"duplicate capability_id: {capability_id}")
        capability_ids.add(capability_id)

        commands = capability.get("verification_commands")
        if not isinstance(commands, list) or not commands:
            raise VerificationError(
                f"verification_commands required for {capability_id}"
            )
        for command in commands:
            if not isinstance(command, dict):
                raise VerificationError("verification command must be an object")
            verification_id = command.get("verification_id")
            if not isinstance(verification_id, str) or not verification_id:
                raise VerificationError("verification_id required")
            if verification_id in verification_ids:
                raise VerificationError(
                    f"duplicate verification_id: {verification_id}"
                )
            verification_ids.add(verification_id)

            script = command.get("script")
            if not isinstance(script, str) or not script:
                raise VerificationError("script required")

            timeout = command.get("timeout_seconds")
            if not isinstance(timeout, int) or timeout < 1 or timeout > 1800:
                raise VerificationError("timeout_seconds must be 1..1800")


def load_config(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise VerificationError(f"file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise VerificationError(f"invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise VerificationError("config must be an object")
    validate_config(value)
    return value


def safety_environment(repository_root: Path) -> dict[str, str]:
    environment = os.environ.copy()
    existing_pythonpath = environment.get("PYTHONPATH", "")
    repository_value = str(repository_root.resolve())
    environment["PYTHONPATH"] = (
        repository_value
        if not existing_pythonpath
        else repository_value + os.pathsep + existing_pythonpath
    )
    environment.update({
        "AI_STOCK_BOT_NETWORK_ALLOWED": "0",
        "AI_STOCK_BOT_BROKER_ENABLED": "0",
        "AI_STOCK_BOT_ORDER_SUBMISSION_ALLOWED": "0",
        "AI_STOCK_BOT_LIVE_TRADING_ALLOWED": "0",
        "PYTHONDONTWRITEBYTECODE": "1",
    })
    return environment


def bounded(text: str, limit: int = 200000) -> tuple[str, bool]:
    if len(text) <= limit:
        return text, False
    return text[-limit:], True


def safe_script(repository_root: Path, relative_value: str) -> Path:
    relative = Path(relative_value)
    if relative.is_absolute() or ".." in relative.parts:
        raise VerificationError(f"unsafe script path: {relative}")
    script = (repository_root / relative).resolve()
    try:
        script.relative_to(repository_root)
    except ValueError as exc:
        raise VerificationError(f"script outside repository: {script}") from exc
    return script


def run_command(
    repository_root: Path,
    capability_id: str,
    specification: dict[str, Any],
) -> dict[str, Any]:
    relative = Path(specification["script"])
    script = safe_script(repository_root, specification["script"])
    record: dict[str, Any] = {
        "capability_id": capability_id,
        "verification_id": specification["verification_id"],
        "script": relative.as_posix(),
        "required": bool(specification.get("required", True)),
        "exists": script.is_file(),
        "status": "NOT_RUN",
        "return_code": None,
        "timed_out": False,
        "duration_seconds": 0.0,
        "stdout": "",
        "stderr": "",
        "stdout_truncated": False,
        "stderr_truncated": False,
        "script_sha256": file_sha256(script) if script.is_file() else None,
    }

    if not script.is_file():
        record["status"] = "MISSING"
        record["record_sha256"] = digest(record)
        return record

    command = [sys.executable, str(script)]
    command.extend(str(value) for value in specification.get("arguments", []))
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
            timeout=specification["timeout_seconds"],
            shell=False,
        )
        stdout, stdout_truncated = bounded(completed.stdout)
        stderr, stderr_truncated = bounded(completed.stderr)
        record.update({
            "status": "PASS" if completed.returncode == 0 else "FAIL",
            "return_code": completed.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "stdout_truncated": stdout_truncated,
            "stderr_truncated": stderr_truncated,
        })
    except subprocess.TimeoutExpired as exc:
        stdout_value = (
            exc.stdout.decode("utf-8", "replace")
            if isinstance(exc.stdout, bytes)
            else (exc.stdout or "")
        )
        stderr_value = (
            exc.stderr.decode("utf-8", "replace")
            if isinstance(exc.stderr, bytes)
            else (exc.stderr or "")
        )
        stdout, stdout_truncated = bounded(stdout_value)
        stderr, stderr_truncated = bounded(stderr_value)
        record.update({
            "status": "TIMEOUT",
            "timed_out": True,
            "stdout": stdout,
            "stderr": stderr,
            "stdout_truncated": stdout_truncated,
            "stderr_truncated": stderr_truncated,
        })

    record["duration_seconds"] = round(time.time() - started, 6)
    record["record_sha256"] = digest({
        key: value for key, value in record.items() if key != "record_sha256"
    })
    return record


def run_verification(
    repository_root: Path,
    config: dict[str, Any],
) -> dict[str, Any]:
    repository_root = repository_root.resolve()
    if not repository_root.is_dir():
        raise VerificationError(f"repository root not found: {repository_root}")

    started = time.time()
    capability_results: list[dict[str, Any]] = []
    all_records: list[dict[str, Any]] = []

    for capability in config["capabilities"]:
        capability_id = capability["capability_id"]
        records = [
            run_command(repository_root, capability_id, command)
            for command in capability["verification_commands"]
        ]
        all_records.extend(records)

        required = [record for record in records if record["required"]]
        passed = sum(record["status"] == "PASS" for record in required)
        failed = sum(
            record["status"] in {"FAIL", "TIMEOUT"} for record in required
        )
        missing = sum(record["status"] == "MISSING" for record in required)
        status = "PASS" if required and passed == len(required) else "FAIL"

        capability_result = {
            "capability_id": capability_id,
            "name": capability["name"],
            "status": status,
            "capability_state": (
                "BEHAVIOR_VERIFIED"
                if status == "PASS"
                else "BEHAVIOR_GAPS_REMAIN"
            ),
            "verification_count": len(records),
            "required_verification_count": len(required),
            "passed_count": passed,
            "failed_count": failed,
            "missing_count": missing,
            "records": records,
            "records_sha256": digest(records),
        }
        capability_result["capability_result_sha256"] = digest(capability_result)
        capability_results.append(capability_result)

    passed_capabilities = sum(
        result["status"] == "PASS" for result in capability_results
    )
    failed_capabilities = len(capability_results) - passed_capabilities
    overall_status = "PASS" if failed_capabilities == 0 else "FAIL"
    failed_ids = [
        result["capability_id"]
        for result in capability_results
        if result["status"] != "PASS"
    ]

    result = {
        "status": overall_status,
        "decision": (
            "multi_capability_behavioral_verification_completed"
            if overall_status == "PASS"
            else "multi_capability_behavioral_verification_failed"
        ),
        "verification_method": "LOCAL_SUBPROCESS_TEST_EXECUTION",
        "capability_count": len(capability_results),
        "passed_capability_count": passed_capabilities,
        "failed_capability_count": failed_capabilities,
        "failed_capability_ids": failed_ids,
        "total_verification_count": len(all_records),
        "capability_results": capability_results,
        "capability_results_sha256": digest(capability_results),
        "duration_seconds": round(time.time() - started, 6),
        "next_phase": (
            "V76_4_ADVANCED_VALIDATION_BEHAVIORAL_VERIFICATION"
            if overall_status == "PASS"
            else "REPAIR_FAILED_CORE_CAPABILITIES"
        ),
        "orders_submitted": 0,
        "cash_mutations": 0,
        "position_mutations": 0,
        "portfolio_mutations": 0,
        "repository_mutations_by_verifier": 0,
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
    main_path = output_dir / "multi_capability_behavioral_verification_v76_3.json"
    summary_path = output_dir / "multi_capability_behavioral_summary_v76_3.json"

    main_path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    summary = {
        "status": result["status"],
        "capability_count": result["capability_count"],
        "passed_capability_count": result["passed_capability_count"],
        "failed_capability_count": result["failed_capability_count"],
        "failed_capability_ids": result["failed_capability_ids"],
        "total_verification_count": result["total_verification_count"],
        "next_phase": result["next_phase"],
        "verification_sha256": result["verification_sha256"],
        "capabilities": [
            {
                "capability_id": item["capability_id"],
                "name": item["name"],
                "status": item["status"],
                "capability_state": item["capability_state"],
                "passed_count": item["passed_count"],
                "failed_count": item["failed_count"],
                "missing_count": item["missing_count"],
            }
            for item in result["capability_results"]
        ],
    }
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return [main_path, summary_path]


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
            "capability_count": result["capability_count"],
            "passed_capability_count": result["passed_capability_count"],
            "failed_capability_count": result["failed_capability_count"],
            "failed_capability_ids": result["failed_capability_ids"],
            "total_verification_count": result["total_verification_count"],
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
            "decision": "multi_capability_behavioral_verification_failed",
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
