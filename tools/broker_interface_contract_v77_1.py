from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, get_type_hints
import sys

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from broker.contracts_v77_1 import (
    AccountSnapshot,
    BrokerCapabilities,
    BrokerContract,
    BrokerEnvironment,
    BrokerHealth,
    BrokerOrder,
    BrokerOrderRequest,
    BrokerOrderStatus,
    BrokerPosition,
    BrokerSafetyPolicy,
    TERMINAL_ORDER_STATUSES,
)

VERSION = "77.1"
SCHEMA = "v77.1.broker_interface_contract.1"
NEXT_PHASE = "V77_2_SANDBOX_BROKER_ADAPTER"


class ContractVerificationError(ValueError):
    pass


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ContractVerificationError(f"required JSON not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ContractVerificationError(f"invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise ContractVerificationError(f"JSON root must be object: {path}")
    return value


def run_git(root: Path, args: list[str]) -> str:
    process = subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True,
        encoding="utf-8", errors="replace", check=False,
    )
    if process.returncode != 0:
        raise ContractVerificationError(
            f"git {' '.join(args)} failed: {process.stderr.strip()}"
        )
    return process.stdout.strip()


def git_state(root: Path) -> dict[str, Any]:
    tracked = run_git(root, ["status", "--short", "--untracked-files=no"])
    return {
        "head_sha": run_git(root, ["rev-parse", "HEAD"]),
        "head_short_sha": run_git(root, ["rev-parse", "--short=7", "HEAD"]),
        "origin_main_sha": run_git(root, ["rev-parse", "origin/main"]),
        "branch": run_git(root, ["rev-parse", "--abbrev-ref", "HEAD"]),
        "tracked_status_short": tracked.splitlines() if tracked else [],
    }


def validate_config(config: dict[str, Any]) -> None:
    if config.get("contract_scope") != "BROKER_INTERFACE_CONTRACT":
        raise ContractVerificationError("contract_scope invalid")
    if config.get("required_environment") != "offline":
        raise ContractVerificationError("required_environment must be offline")
    for key in (
        "require_runtime_protocol",
        "require_immutable_contract_models",
        "require_decimal_financial_fields",
        "require_terminal_status_definition",
        "require_source_anchor_match",
    ):
        if config.get(key) is not True:
            raise ContractVerificationError(f"{key} must be true")
    for key in (
        "network_allowed",
        "broker_connection_allowed",
        "order_submission_allowed",
        "live_trading_allowed",
        "live_approval_allowed",
    ):
        if config.get(key) is not False:
            raise ContractVerificationError(f"{key} must be false")


def add_gate(gates: list[dict[str, Any]], gate_id: str, passed: bool, detail: str = "") -> None:
    gates.append(
        {"gate_id": gate_id, "status": "PASS" if passed else "FAIL", "detail": detail}
    )


def verify_contract(root: Path, config: dict[str, Any]) -> dict[str, Any]:
    root = root.resolve()
    validate_config(config)
    git = git_state(root)
    gates: list[dict[str, Any]] = []

    add_gate(gates, "GIT_HEAD_MATCHES_ORIGIN_MAIN", git["head_sha"] == git["origin_main_sha"])
    add_gate(
        gates,
        "GIT_HEAD_MATCHES_FRAMEWORK_COMMIT",
        git["head_short_sha"] == config["expected_framework_commit_sha"],
    )
    add_gate(gates, "GIT_BRANCH_MAIN", git["branch"] == "main")
    add_gate(gates, "GIT_TRACKED_WORKING_TREE_CLEAN", git["tracked_status_short"] == [])

    closure_summary_path = root / "release/v76_24/output/project_release_closure_summary_v76_24.json"
    closure_path = root / "release/v76_24/output/project_release_closure_v76_24.json"
    add_gate(gates, "V76_24_CLOSURE_EXISTS", closure_path.is_file())
    add_gate(gates, "V76_24_CLOSURE_SUMMARY_EXISTS", closure_summary_path.is_file())
    closure = load_json(closure_path)
    closure_summary = load_json(closure_summary_path)

    add_gate(
        gates,
        "V76_24_CLOSURE_FIXED_ANCHOR",
        closure.get("closure_sha256") == config["expected_v76_24_closure_sha256"],
    )
    add_gate(
        gates,
        "V76_24_CLOSURE_CHAIN_FIXED_ANCHOR",
        closure.get("closure_chain_sha256")
        == config["expected_v76_24_closure_chain_sha256"],
    )
    add_gate(gates, "V76_24_STATUS_PASS", closure.get("status") == "PASS")
    add_gate(
        gates,
        "V76_24_PROJECT_RELEASE_CLOSED",
        closure.get("project_release_closed") is True,
    )
    add_gate(
        gates,
        "V76_24_OFFLINE_PAPER_COMPLETE",
        closure.get("offline_paper_release_complete") is True,
    )
    add_gate(
        gates,
        "V76_24_SUMMARY_ANCHOR_MATCH",
        closure_summary.get("closure_sha256") == closure.get("closure_sha256"),
    )

    policy = BrokerSafetyPolicy()
    policy_ok = True
    try:
        policy.validate()
    except Exception:
        policy_ok = False
    add_gate(gates, "DEFAULT_SAFETY_POLICY_VALID", policy_ok)
    add_gate(gates, "DEFAULT_ENVIRONMENT_OFFLINE", policy.environment is BrokerEnvironment.OFFLINE)
    add_gate(gates, "DEFAULT_NETWORK_DISABLED", policy.network_allowed is False)
    add_gate(gates, "DEFAULT_ORDER_SUBMISSION_DISABLED", policy.order_submission_allowed is False)
    add_gate(gates, "DEFAULT_LIVE_AUTHORIZATION_DISABLED", policy.live_trading_authorized is False)

    protocol_methods = {
        name
        for name, value in inspect.getmembers(BrokerContract)
        if callable(value) and not name.startswith("_")
    }
    required_methods = {
        "health",
        "get_account_snapshot",
        "list_orders",
        "get_order",
        "submit_order",
        "cancel_order",
    }
    add_gate(gates, "BROKER_PROTOCOL_METHODS_COMPLETE", required_methods <= protocol_methods)
    add_gate(
        gates,
        "ORDER_STATUS_TERMINALS_DEFINED",
        {
            BrokerOrderStatus.REJECTED,
            BrokerOrderStatus.SUBMISSION_BLOCKED,
            BrokerOrderStatus.FILLED,
            BrokerOrderStatus.CANCELED,
            BrokerOrderStatus.EXPIRED,
            BrokerOrderStatus.ERROR,
        }
        <= TERMINAL_ORDER_STATUSES,
    )

    model_types = [
        BrokerCapabilities,
        BrokerOrderRequest,
        BrokerOrder,
        BrokerPosition,
        AccountSnapshot,
        BrokerHealth,
        BrokerSafetyPolicy,
    ]
    immutable = all(getattr(t, "__dataclass_params__").frozen for t in model_types)
    add_gate(gates, "CONTRACT_MODELS_IMMUTABLE", immutable)

    type_contract = {
        "BrokerOrderRequest": sorted(get_type_hints(BrokerOrderRequest).keys()),
        "BrokerOrder": sorted(get_type_hints(BrokerOrder).keys()),
        "BrokerPosition": sorted(get_type_hints(BrokerPosition).keys()),
        "AccountSnapshot": sorted(get_type_hints(AccountSnapshot).keys()),
        "BrokerHealth": sorted(get_type_hints(BrokerHealth).keys()),
        "BrokerCapabilities": sorted(get_type_hints(BrokerCapabilities).keys()),
        "BrokerSafetyPolicy": sorted(get_type_hints(BrokerSafetyPolicy).keys()),
        "BrokerContractMethods": sorted(required_methods),
        "TerminalStatuses": sorted(s.value for s in TERMINAL_ORDER_STATUSES),
    }
    contract_sha = digest(type_contract)
    add_gate(gates, "CONTRACT_DIGEST_CREATED", len(contract_sha) == 64)

    failed = [g["gate_id"] for g in gates if g["status"] == "FAIL"]
    result = {
        "schema_version": SCHEMA,
        "version": VERSION,
        "record_type": "BROKER_INTERFACE_CONTRACT_VERIFICATION",
        "issued_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS" if not failed else "FAIL",
        "decision": (
            "broker_interface_contract_established"
            if not failed else "broker_interface_contract_rejected"
        ),
        "repository": {
            "framework_commit_sha": git["head_sha"],
            "origin_main_sha": git["origin_main_sha"],
            "branch": git["branch"],
            "tracked_working_tree_clean": git["tracked_status_short"] == [],
        },
        "source_anchors": {
            "v76_24_closure_sha256": closure.get("closure_sha256"),
            "v76_24_closure_chain_sha256": closure.get("closure_chain_sha256"),
        },
        "contract_definition": type_contract,
        "broker_contract_sha256": contract_sha,
        "verification_result": {
            "gate_count": len(gates),
            "passed_gate_count": len(gates) - len(failed),
            "failed_gate_count": len(failed),
            "failed_gate_ids": failed,
            "gates": gates,
        },
        "environment": "offline",
        "network_allowed": False,
        "broker_connected": False,
        "orders_submitted": 0,
        "order_submission_allowed": False,
        "approved_for_live": False,
        "live_trading_authorized": False,
        "next_phase": NEXT_PHASE if not failed else "REPAIR_V77_1_BROKER_INTERFACE_CONTRACT",
    }
    result["verification_sha256"] = digest(
        {k: v for k, v in result.items() if k not in {"verification_sha256", "issued_at_utc"}}
    )
    return result


def summary_from(result: dict[str, Any]) -> dict[str, Any]:
    vr = result["verification_result"]
    return {
        "status": result["status"],
        "decision": result["decision"],
        "framework_commit_sha": result["repository"]["framework_commit_sha"],
        "broker_contract_sha256": result["broker_contract_sha256"],
        "verification_sha256": result["verification_sha256"],
        **result["source_anchors"],
        "gate_count": vr["gate_count"],
        "passed_gate_count": vr["passed_gate_count"],
        "failed_gate_count": vr["failed_gate_count"],
        "failed_gate_ids": vr["failed_gate_ids"],
        "environment": result["environment"],
        "network_allowed": result["network_allowed"],
        "broker_connected": result["broker_connected"],
        "orders_submitted": result["orders_submitted"],
        "order_submission_allowed": result["order_submission_allowed"],
        "live_trading_authorized": result["live_trading_authorized"],
        "next_phase": result["next_phase"],
    }


def write_outputs(result: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "broker_interface_contract_verification_v77_1.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / "broker_interface_contract_summary_v77_1.json").write_text(
        json.dumps(summary_from(result), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def cli() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    result = verify_contract(Path(args.repository_root), load_json(Path(args.config)))
    write_outputs(result, Path(args.output_dir))
    print(json.dumps(summary_from(result), indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(cli())
