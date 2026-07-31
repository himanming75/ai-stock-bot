from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

VERSION = "76.5"
SCHEMA = "v76.5.release_candidate_system_acceptance.1"


class AcceptanceError(ValueError):
    pass


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise AcceptanceError(f"required JSON not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise AcceptanceError(f"invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise AcceptanceError(f"JSON root must be object: {path}")
    return value


def validate_config(config: dict[str, Any]) -> None:
    if config.get("acceptance_scope") != "RELEASE_CANDIDATE_SYSTEM_ACCEPTANCE":
        raise AcceptanceError("acceptance_scope invalid")

    true_keys = (
        "offline_only",
        "preserve_repository",
        "require_prior_verification_pass",
        "require_deterministic_model_output",
        "require_zero_trading_side_effects",
        "require_tracked_file_immutability",
        "require_all_gates_pass",
    )
    false_keys = (
        "network_allowed",
        "broker_connection_allowed",
        "order_submission_allowed",
        "live_trading_allowed",
        "live_approval_allowed",
    )
    for key in true_keys:
        if config.get(key) is not True:
            raise AcceptanceError(f"{key} must be true")
    for key in false_keys:
        if config.get(key) is not False:
            raise AcceptanceError(f"{key} must be false")

    timeout = config.get("command_timeout_seconds")
    if not isinstance(timeout, int) or not 60 <= timeout <= 7200:
        raise AcceptanceError("command_timeout_seconds must be 60..7200")


def safety_environment(root: Path) -> dict[str, str]:
    env = os.environ.copy()
    root_text = str(root.resolve())
    current = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = root_text if not current else root_text + os.pathsep + current
    env.update({
        "AI_STOCK_BOT_NETWORK_ALLOWED": "0",
        "AI_STOCK_BOT_BROKER_ENABLED": "0",
        "AI_STOCK_BOT_ORDER_SUBMISSION_ALLOWED": "0",
        "AI_STOCK_BOT_LIVE_TRADING_ALLOWED": "0",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONHASHSEED": "0",
        "TZ": "UTC",
    })
    return env


def git_tracked_snapshot(root: Path) -> dict[str, str]:
    completed = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=root,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise AcceptanceError(
            "git ls-files failed: " + completed.stderr.decode("utf-8", "replace")
        )
    result: dict[str, str] = {}
    for raw in completed.stdout.split(b"\0"):
        if not raw:
            continue
        name = raw.decode("utf-8", "surrogateescape")
        path = root / name
        result[name.replace("\\", "/")] = (
            file_sha256(path) if path.is_file() else "<MISSING>"
        )
    return result


def git_diff_state(root: Path) -> dict[str, Any]:
    worktree = subprocess.run(
        ["git", "diff", "--name-only"],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    staged = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if worktree.returncode != 0 or staged.returncode != 0:
        raise AcceptanceError("git diff inspection failed")
    return {
        "modified_tracked_files": sorted(
            line.strip() for line in worktree.stdout.splitlines() if line.strip()
        ),
        "staged_files": sorted(
            line.strip() for line in staged.stdout.splitlines() if line.strip()
        ),
    }


def run_command(
    root: Path,
    command: list[str],
    timeout: int,
    environment: dict[str, str],
) -> dict[str, Any]:
    started = time.time()
    try:
        completed = subprocess.run(
            command,
            cwd=root,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            shell=False,
        )
        return {
            "status": "PASS" if completed.returncode == 0 else "FAIL",
            "return_code": completed.returncode,
            "timed_out": False,
            "duration_seconds": round(time.time() - started, 6),
            "stdout": completed.stdout[-200000:],
            "stderr": completed.stderr[-200000:],
            "command": command,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "status": "TIMEOUT",
            "return_code": None,
            "timed_out": True,
            "duration_seconds": round(time.time() - started, 6),
            "stdout": (exc.stdout or "")[-200000:] if isinstance(exc.stdout, str) else "",
            "stderr": (exc.stderr or "")[-200000:] if isinstance(exc.stderr, str) else "",
            "command": command,
        }


def prior_evidence_gate(root: Path, config: dict[str, Any]) -> dict[str, Any]:
    full_path = root / config["prior_verification_path"]
    summary_path = root / config["prior_summary_path"]
    full = load_json(full_path)
    summary = load_json(summary_path)

    conditions = {
        "full_status_pass": full.get("status") == "PASS",
        "summary_status_pass": summary.get("status") == "PASS",
        "failed_scenario_count_zero": full.get("failed_scenario_count") == 0,
        "all_outputs_repeatable": full.get("all_outputs_repeatable") is True,
        "tracked_file_immutability_verified":
            full.get("tracked_file_immutability_verified") is True,
        "orders_submitted_zero": full.get("orders_submitted") == 0,
        "network_disallowed": full.get("network_allowed") is False,
        "live_not_approved": full.get("approved_for_live") is False,
        "next_phase_correct":
            full.get("next_phase") == "V76_5_RELEASE_CANDIDATE_SYSTEM_ACCEPTANCE",
        "summary_hash_matches":
            summary.get("verification_sha256") == full.get("verification_sha256"),
    }
    status = "PASS" if all(conditions.values()) else "FAIL"
    return {
        "gate_id": "PRIOR_V76_4_EVIDENCE",
        "status": status,
        "conditions": conditions,
        "verification_sha256": full.get("verification_sha256"),
        "full_evidence_file_sha256": file_sha256(full_path),
        "summary_evidence_file_sha256": file_sha256(summary_path),
    }


def command_gate(
    gate_id: str,
    result: dict[str, Any],
    extra_conditions: dict[str, bool] | None = None,
) -> dict[str, Any]:
    conditions = {"command_passed": result["status"] == "PASS"}
    if extra_conditions:
        conditions.update(extra_conditions)
    return {
        "gate_id": gate_id,
        "status": "PASS" if all(conditions.values()) else "FAIL",
        "conditions": conditions,
        "execution": result,
    }


def run_acceptance(root: Path, config: dict[str, Any]) -> dict[str, Any]:
    root = root.resolve()
    if not root.is_dir():
        raise AcceptanceError(f"repository root not found: {root}")

    validate_config(config)
    timeout = config["command_timeout_seconds"]
    env = safety_environment(root)
    started = time.time()

    before_snapshot = git_tracked_snapshot(root)
    before_diff = git_diff_state(root)
    gates: list[dict[str, Any]] = []

    gates.append(prior_evidence_gate(root, config))

    unit_result = run_command(
        root,
        [
            sys.executable,
            "-m",
            "unittest",
            "tools.test_apply_deterministic_ml_repair_v76_4b",
            "-v",
        ],
        timeout,
        env,
    )
    gates.append(command_gate("V76_4B_REPAIR_UNIT_TESTS", unit_result))

    ml_first = run_command(root, [sys.executable, "test_ml.py"], timeout, env)
    ml_second = run_command(root, [sys.executable, "test_ml.py"], timeout, env)
    deterministic_conditions = {
        "first_run_passed": ml_first["status"] == "PASS",
        "second_run_passed": ml_second["status"] == "PASS",
        "stdout_identical": ml_first["stdout"] == ml_second["stdout"],
        "stderr_identical": ml_first["stderr"] == ml_second["stderr"],
    }
    gates.append({
        "gate_id": "MODEL_OUTPUT_DETERMINISM",
        "status": "PASS" if all(deterministic_conditions.values()) else "FAIL",
        "conditions": deterministic_conditions,
        "first_execution": ml_first,
        "second_execution": ml_second,
        "output_sha256": digest({
            "stdout": ml_first["stdout"],
            "stderr": ml_first["stderr"],
        }),
    })

    with tempfile.TemporaryDirectory(prefix="v76_5_acceptance_") as temp_dir:
        verification_result = run_command(
            root,
            [
                sys.executable,
                "tools/advanced_validation_behavioral_verification_v76_4.py",
                "--repository-root",
                ".",
                "--config",
                config["prior_config_path"],
                "--output-dir",
                temp_dir,
            ],
            timeout,
            env,
        )
        generated_summary_path = (
            Path(temp_dir) / "advanced_validation_behavioral_summary_v76_4.json"
        )
        generated_summary = (
            load_json(generated_summary_path)
            if generated_summary_path.is_file()
            else {}
        )
        rerun_conditions = {
            "command_passed": verification_result["status"] == "PASS",
            "summary_created": generated_summary_path.is_file(),
            "summary_status_pass": generated_summary.get("status") == "PASS",
            "failed_scenario_count_zero":
                generated_summary.get("failed_scenario_count") == 0,
            "all_outputs_repeatable":
                generated_summary.get("all_outputs_repeatable") is True,
            "tracked_file_immutability_verified":
                generated_summary.get("tracked_file_immutability_verified") is True,
        }
        gates.append({
            "gate_id": "FULL_V76_4_REVERIFICATION",
            "status": "PASS" if all(rerun_conditions.values()) else "FAIL",
            "conditions": rerun_conditions,
            "execution": verification_result,
            "generated_summary": generated_summary,
        })

    after_snapshot = git_tracked_snapshot(root)
    after_diff = git_diff_state(root)
    changed_during_acceptance = sorted(
        name for name in set(before_snapshot) | set(after_snapshot)
        if before_snapshot.get(name) != after_snapshot.get(name)
    )
    repository_conditions = {
        "no_tracked_file_changed_during_acceptance":
            not changed_during_acceptance,
        "no_modified_tracked_files_before":
            not before_diff["modified_tracked_files"],
        "no_staged_files_before":
            not before_diff["staged_files"],
        "no_modified_tracked_files_after":
            not after_diff["modified_tracked_files"],
        "no_staged_files_after":
            not after_diff["staged_files"],
    }
    gates.append({
        "gate_id": "REPOSITORY_INTEGRITY",
        "status": "PASS" if all(repository_conditions.values()) else "FAIL",
        "conditions": repository_conditions,
        "changed_during_acceptance": changed_during_acceptance,
        "before_diff": before_diff,
        "after_diff": after_diff,
    })

    failed_gate_ids = [
        gate["gate_id"] for gate in gates if gate["status"] != "PASS"
    ]
    status = "PASS" if not failed_gate_ids else "FAIL"

    result = {
        "status": status,
        "decision": (
            "release_candidate_system_acceptance_completed"
            if status == "PASS"
            else "release_candidate_system_acceptance_failed"
        ),
        "version": VERSION,
        "schema_version": SCHEMA,
        "gate_count": len(gates),
        "passed_gate_count": len(gates) - len(failed_gate_ids),
        "failed_gate_count": len(failed_gate_ids),
        "failed_gate_ids": failed_gate_ids,
        "gates": gates,
        "tracked_file_immutability_verified": not changed_during_acceptance,
        "changed_tracked_files": changed_during_acceptance,
        "orders_submitted": 0,
        "cash_mutations": 0,
        "position_mutations": 0,
        "portfolio_mutations": 0,
        "network_allowed": False,
        "broker_connected": False,
        "approved_for_live": False,
        "release_candidate_accepted": status == "PASS",
        "next_phase": (
            "V76_6_RELEASE_CANDIDATE_EVIDENCE_SEAL"
            if status == "PASS"
            else "REPAIR_RELEASE_CANDIDATE_ACCEPTANCE_GAPS"
        ),
        "duration_seconds": round(time.time() - started, 6),
    }
    result["acceptance_sha256"] = digest(result)
    return result


def write_outputs(result: dict[str, Any], output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    full_path = output_dir / "release_candidate_system_acceptance_v76_5.json"
    summary_path = output_dir / "release_candidate_system_acceptance_summary_v76_5.json"

    full_path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    summary = {
        "status": result["status"],
        "decision": result["decision"],
        "gate_count": result["gate_count"],
        "passed_gate_count": result["passed_gate_count"],
        "failed_gate_count": result["failed_gate_count"],
        "failed_gate_ids": result["failed_gate_ids"],
        "tracked_file_immutability_verified":
            result["tracked_file_immutability_verified"],
        "changed_tracked_files": result["changed_tracked_files"],
        "orders_submitted": result["orders_submitted"],
        "network_allowed": result["network_allowed"],
        "approved_for_live": result["approved_for_live"],
        "release_candidate_accepted": result["release_candidate_accepted"],
        "next_phase": result["next_phase"],
        "acceptance_sha256": result["acceptance_sha256"],
        "gates": [
            {
                "gate_id": gate["gate_id"],
                "status": gate["status"],
                "conditions": gate["conditions"],
            }
            for gate in result["gates"]
        ],
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
        config = load_json(Path(args.config))
        result = run_acceptance(Path(args.repository_root), config)
        outputs = write_outputs(result, Path(args.output_dir))
    except (AcceptanceError, OSError, ValueError) as exc:
        print(json.dumps({
            "status": "ERROR",
            "error": str(exc),
            "approved_for_live": False,
        }, indent=2, sort_keys=True))
        return 2

    print(json.dumps({
        "status": result["status"],
        "decision": result["decision"],
        "gate_count": result["gate_count"],
        "passed_gate_count": result["passed_gate_count"],
        "failed_gate_count": result["failed_gate_count"],
        "failed_gate_ids": result["failed_gate_ids"],
        "tracked_file_immutability_verified":
            result["tracked_file_immutability_verified"],
        "changed_tracked_files": result["changed_tracked_files"],
        "orders_submitted": result["orders_submitted"],
        "network_allowed": result["network_allowed"],
        "approved_for_live": result["approved_for_live"],
        "release_candidate_accepted": result["release_candidate_accepted"],
        "next_phase": result["next_phase"],
        "outputs": [str(path) for path in outputs],
        "acceptance_sha256": result["acceptance_sha256"],
    }, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
