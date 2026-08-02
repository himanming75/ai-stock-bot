from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON object required: {path}")
    return payload


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(payload, sort_keys=True) + "\n")


def _stable_id(prefix: str, *parts: str) -> str:
    identity = "|".join(parts)
    return prefix + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24]


class UltraFastCycleFinalization:
    def run(
        self,
        *,
        completion_result_path: Path,
        completion_token_path: Path,
        terminal_token_path: Path,
        portfolio_snapshot_path: Path,
        reconciliation_result_path: Path,
        pnl_result_path: Path,
        execution_ledger_path: Path,
        archive_manifest_path: Path,
        bootstrap_token_path: Path,
        result_path: Path,
    ) -> dict[str, Any]:
        issues: list[dict[str, Any]] = []

        try:
            completion = _load_json(completion_result_path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            completion = {}
            issues.append({"code": "INVALID_COMPLETION_RESULT", "blocking": True, "detail": str(exc)})

        if not completion:
            issues.append({
                "code": "COMPLETION_RESULT_NOT_FOUND",
                "blocking": True,
                "detail": str(completion_result_path),
            })

        source_status = str(completion.get("status", "")).upper()
        source_state = str(completion.get("state", "")).upper()
        source_safe_mode = bool(completion.get("safe_mode_engaged", False))
        cycle_completed = bool(completion.get("cycle_completed", False))
        next_cycle_handoff_ready = bool(completion.get("next_cycle_handoff_ready", False))
        completion_id = str(completion.get("completion_id", "")).strip()
        client_order_id = str(completion.get("client_order_id", "")).strip()
        broker_order_id = str(completion.get("broker_order_id", "")).strip()
        final_status = str(completion.get("final_order_status", "")).strip().upper()

        if source_safe_mode or source_status == "BLOCKED":
            issues.append({
                "code": "SOURCE_COMPLETION_SAFE_MODE",
                "blocking": True,
                "detail": "V139.10 is blocked or in safe mode",
            })

        finalize_required = (
            cycle_completed
            or next_cycle_handoff_ready
            or source_state == "CYCLE_COMPLETED"
        )

        completion_token: dict[str, Any] = {}
        terminal_token: dict[str, Any] = {}
        portfolio: dict[str, Any] = {}

        if finalize_required:
            for code, path in (
                ("COMPLETION_TOKEN", completion_token_path),
                ("TERMINAL_TOKEN", terminal_token_path),
                ("PORTFOLIO_SNAPSHOT", portfolio_snapshot_path),
            ):
                try:
                    loaded = _load_json(path)
                except (OSError, ValueError, json.JSONDecodeError) as exc:
                    loaded = {}
                    issues.append({"code": f"INVALID_{code}", "blocking": True, "detail": str(exc)})
                if code == "COMPLETION_TOKEN":
                    completion_token = loaded
                elif code == "TERMINAL_TOKEN":
                    terminal_token = loaded
                else:
                    portfolio = loaded
                if not loaded:
                    issues.append({
                        "code": f"{code}_NOT_FOUND",
                        "blocking": True,
                        "detail": str(path),
                    })

        if completion_token and (
            completion_token.get("completion_id") != completion_id
            or not bool(completion_token.get("cycle_completed", False))
        ):
            issues.append({
                "code": "COMPLETION_TOKEN_MISMATCH",
                "blocking": True,
                "detail": "completion token does not match V139.10 result",
            })

        if terminal_token and (
            terminal_token.get("completion_id") != completion_id
            or not bool(terminal_token.get("terminal_commit_verified", False))
        ):
            issues.append({
                "code": "TERMINAL_TOKEN_MISMATCH",
                "blocking": True,
                "detail": "terminal token does not match V139.10 result",
            })

        if portfolio:
            required_fields = (
                "local_cash",
                "broker_cash",
                "local_equity",
                "broker_equity",
                "local_position_quantity",
                "broker_position_quantity",
            )
            for field in required_fields:
                if field not in portfolio:
                    issues.append({
                        "code": "PORTFOLIO_FIELD_MISSING",
                        "blocking": True,
                        "detail": field,
                    })

        try:
            local_cash = float(portfolio.get("local_cash", 0) or 0)
            broker_cash = float(portfolio.get("broker_cash", 0) or 0)
            local_equity = float(portfolio.get("local_equity", 0) or 0)
            broker_equity = float(portfolio.get("broker_equity", 0) or 0)
            local_position = float(portfolio.get("local_position_quantity", 0) or 0)
            broker_position = float(portfolio.get("broker_position_quantity", 0) or 0)
            starting_equity = float(portfolio.get("starting_equity", local_equity) or 0)
            fees = float(portfolio.get("fees", 0) or 0)
        except (TypeError, ValueError):
            local_cash = broker_cash = local_equity = broker_equity = 0.0
            local_position = broker_position = starting_equity = fees = 0.0
            issues.append({
                "code": "INVALID_PORTFOLIO_NUMERIC_VALUE",
                "blocking": True,
                "detail": "portfolio values must be numeric",
            })

        tolerance = float(portfolio.get("tolerance", 0.01) or 0.01) if portfolio else 0.01
        cash_difference = broker_cash - local_cash
        equity_difference = broker_equity - local_equity
        position_difference = broker_position - local_position

        if portfolio:
            if abs(cash_difference) > tolerance:
                issues.append({"code": "CASH_MISMATCH", "blocking": True, "detail": str(cash_difference)})
            if abs(equity_difference) > tolerance:
                issues.append({"code": "EQUITY_MISMATCH", "blocking": True, "detail": str(equity_difference)})
            if abs(position_difference) > tolerance:
                issues.append({"code": "POSITION_MISMATCH", "blocking": True, "detail": str(position_difference)})

        blocking = sum(1 for issue in issues if issue.get("blocking"))
        safe_mode = blocking > 0

        completion_verified = bool(
            source_status == "PASS"
            and source_state == "CYCLE_COMPLETED"
            and cycle_completed
            and next_cycle_handoff_ready
            and completion_id
            and client_order_id
            and broker_order_id
            and completion_token
            and terminal_token
            and not safe_mode
        )
        portfolio_reconciled = bool(portfolio and not safe_mode)
        pnl_settled = False
        execution_ledger_finalized = False
        archive_created = False
        bootstrap_ready = False
        duplicate_bootstrap = False

        net_pnl = broker_equity - starting_equity - fees if portfolio else 0.0
        settlement_id = _stable_id("settlement-", completion_id, f"{net_pnl:.8f}") if completion_verified and portfolio_reconciled else ""
        archive_id = _stable_id("archive-", completion_id, settlement_id) if settlement_id else ""
        bootstrap_id = _stable_id("bootstrap-", completion_id, archive_id) if archive_id else ""

        if completion_verified and portfolio_reconciled:
            reconciliation_payload = {
                "stage": "V139.11",
                "completion_id": completion_id,
                "portfolio_reconciled": True,
                "cash_difference": cash_difference,
                "equity_difference": equity_difference,
                "position_difference": position_difference,
                "tolerance": tolerance,
                "captured_at": datetime.now(timezone.utc).isoformat(),
            }
            _atomic_write_json(reconciliation_result_path, reconciliation_payload)

            pnl_payload = {
                "stage": "V139.12",
                "completion_id": completion_id,
                "settlement_id": settlement_id,
                "starting_equity": starting_equity,
                "ending_equity": broker_equity,
                "fees": fees,
                "net_pnl": net_pnl,
                "pnl_settled": True,
                "captured_at": datetime.now(timezone.utc).isoformat(),
            }
            _atomic_write_json(pnl_result_path, pnl_payload)
            pnl_settled = True

            ledger_event = {
                "event": "EXECUTION_LEDGER_FINALIZED",
                "stage": "V139.13",
                "completion_id": completion_id,
                "settlement_id": settlement_id,
                "client_order_id": client_order_id,
                "broker_order_id": broker_order_id,
                "final_order_status": final_status,
                "net_pnl": net_pnl,
                "finalized_at": datetime.now(timezone.utc).isoformat(),
            }
            existing_lines = execution_ledger_path.read_text(encoding="utf-8").splitlines() if execution_ledger_path.exists() else []
            if not any(completion_id in line for line in existing_lines):
                _append_jsonl(execution_ledger_path, ledger_event)
            execution_ledger_finalized = True

            archive_payload = {
                "stage": "V139.14",
                "archive_id": archive_id,
                "completion_id": completion_id,
                "settlement_id": settlement_id,
                "source_files": [
                    str(completion_result_path.resolve()),
                    str(completion_token_path.resolve()),
                    str(terminal_token_path.resolve()),
                    str(portfolio_snapshot_path.resolve()),
                    str(reconciliation_result_path.resolve()),
                    str(pnl_result_path.resolve()),
                    str(execution_ledger_path.resolve()),
                ],
                "archive_created": True,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            _atomic_write_json(archive_manifest_path, archive_payload)
            archive_created = True

            bootstrap_payload = {
                "stage": "V139.15",
                "bootstrap_id": bootstrap_id,
                "previous_completion_id": completion_id,
                "archive_id": archive_id,
                "previous_cycle_closed": True,
                "next_cycle_bootstrap_ready": True,
                "next_phase": "V140_01_AUTONOMOUS_RUNTIME_SUPERVISOR",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            if bootstrap_token_path.exists():
                existing = _load_json(bootstrap_token_path)
                if existing.get("bootstrap_id") == bootstrap_id:
                    duplicate_bootstrap = True
                else:
                    issues.append({
                        "code": "BOOTSTRAP_TOKEN_CONFLICT",
                        "blocking": True,
                        "detail": "existing bootstrap token belongs to another cycle",
                    })
            else:
                _atomic_write_json(bootstrap_token_path, bootstrap_payload)

            blocking = sum(1 for issue in issues if issue.get("blocking"))
            safe_mode = blocking > 0
            bootstrap_ready = bool(not safe_mode)

        if safe_mode:
            state = "ULTRA_FINALIZATION_SAFE_MODE"
            status = "BLOCKED"
        elif bootstrap_ready:
            state = "NEXT_CYCLE_BOOTSTRAP_READY"
            status = "PASS"
        else:
            state = "WAIT_CYCLE_COMPLETION"
            status = "PASS"

        result = {
            "actual_credentials_used": False,
            "actual_external_network_used": False,
            "actual_paper_orders_submitted": 0,
            "archive_created": archive_created,
            "archive_id": archive_id,
            "blocking_issue_count": sum(1 for issue in issues if issue.get("blocking")),
            "bootstrap_id": bootstrap_id,
            "completion_id": completion_id,
            "completion_verified": completion_verified,
            "duplicate_bootstrap": duplicate_bootstrap,
            "execution_ledger_finalized": execution_ledger_finalized,
            "implementation_type": "ULTRA_FAST_CYCLE_FINALIZATION",
            "issue_count": len(issues),
            "issues": issues,
            "live_orders_submitted": 0,
            "network_requests_executed": 0,
            "next_cycle_bootstrap_ready": bootstrap_ready,
            "next_phase": (
                "V140_01_AUTONOMOUS_RUNTIME_SUPERVISOR"
                if bootstrap_ready and not safe_mode
                else "V139_11_TO_V139_15_WAIT_CYCLE_COMPLETION"
            ),
            "pnl_settled": pnl_settled,
            "portfolio_reconciled": portfolio_reconciled,
            "safe_mode_engaged": safe_mode,
            "settlement_id": settlement_id,
            "stage_range": "V139.11-V139.15",
            "state": state,
            "status": status,
            "validation_mode": "LOCAL_ULTRA_FAST_FINALIZATION_ONLY",
            "write_requests_executed": 0,
            "result_path": str(result_path.resolve()),
            "observed_at": datetime.now(timezone.utc).isoformat(),
        }
        _atomic_write_json(result_path, result)
        return result
