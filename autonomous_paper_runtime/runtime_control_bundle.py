from __future__ import annotations

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


def _atomic_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


class RuntimeControlBundle:
    def run(
        self,
        *,
        runtime_result_path: Path,
        runtime_token_path: Path,
        market_snapshot_path: Path,
        daily_risk_snapshot_path: Path,
        health_snapshot_path: Path,
        result_path: Path,
        control_token_path: Path,
    ) -> dict[str, Any]:
        issues: list[dict[str, Any]] = []

        try:
            runtime = _load_json(runtime_result_path)
        except Exception as exc:
            runtime = {}
            issues.append({"code": "INVALID_RUNTIME_RESULT", "blocking": True, "detail": str(exc)})

        if not runtime:
            issues.append({"code": "RUNTIME_RESULT_NOT_FOUND", "blocking": True, "detail": str(runtime_result_path)})

        runtime_ready = bool(runtime.get("runtime_ready", False))
        runtime_state = str(runtime.get("state", "")).upper()
        runtime_status = str(runtime.get("status", "")).upper()
        runtime_safe = bool(runtime.get("safe_mode_engaged", False))
        runtime_cycle_id = str(runtime.get("runtime_cycle_id", "")).strip()

        if runtime_safe or runtime_status == "BLOCKED":
            issues.append({"code": "SOURCE_RUNTIME_SAFE_MODE", "blocking": True, "detail": runtime_state})

        gates_required = runtime_ready or runtime_state == "AUTONOMOUS_RUNTIME_READY"
        token = market = risk = health = {}

        if gates_required:
            for name, path in (
                ("RUNTIME_TOKEN", runtime_token_path),
                ("MARKET_SNAPSHOT", market_snapshot_path),
                ("DAILY_RISK_SNAPSHOT", daily_risk_snapshot_path),
                ("HEALTH_SNAPSHOT", health_snapshot_path),
            ):
                try:
                    loaded = _load_json(path)
                except Exception as exc:
                    loaded = {}
                    issues.append({"code": f"INVALID_{name}", "blocking": True, "detail": str(exc)})
                if name == "RUNTIME_TOKEN":
                    token = loaded
                elif name == "MARKET_SNAPSHOT":
                    market = loaded
                elif name == "DAILY_RISK_SNAPSHOT":
                    risk = loaded
                else:
                    health = loaded
                if not loaded:
                    issues.append({"code": f"{name}_NOT_FOUND", "blocking": True, "detail": str(path)})

        if token and (
            token.get("runtime_cycle_id") != runtime_cycle_id
            or not bool(token.get("runtime_ready", False))
            or bool(token.get("actual_submission_allowed", True))
            or bool(token.get("broker_network_allowed", True))
        ):
            issues.append({"code": "RUNTIME_TOKEN_MISMATCH", "blocking": True, "detail": "local-only runtime contract mismatch"})

        market_phase = str(market.get("market_phase", "")).upper()
        market_session_ready = False
        if market:
            if market_phase not in {"PRE_MARKET", "MARKET_OPEN", "TRADING_WINDOW", "NO_NEW_ORDER_WINDOW", "MARKET_CLOSED", "POST_MARKET"}:
                issues.append({"code": "INVALID_MARKET_PHASE", "blocking": True, "detail": market_phase})
            market_session_ready = bool(
                market_phase in {"MARKET_OPEN", "TRADING_WINDOW"}
                and bool(market.get("market_is_open", False))
                and bool(market.get("new_orders_allowed", False))
                and not bool(market.get("holiday", False))
            )
            if not market_session_ready:
                issues.append({
                    "code": "MARKET_SESSION_NOT_TRADABLE",
                    "blocking": True,
                    "detail": (
                        f"phase={market_phase}, "
                        f"market_is_open={bool(market.get('market_is_open', False))}, "
                        f"new_orders_allowed={bool(market.get('new_orders_allowed', False))}, "
                        f"holiday={bool(market.get('holiday', False))}"
                    ),
                })

        daily_risk_ready = False
        if risk:
            checks = [
                ("DAILY_ORDER_LIMIT", int(risk.get("orders_used", 0)) < int(risk.get("max_daily_orders", 0))),
                ("DAILY_LOSS_LIMIT", float(risk.get("daily_pnl", 0)) > -abs(float(risk.get("max_daily_loss", 0)))),
                ("EXPOSURE_LIMIT", float(risk.get("current_exposure", 0)) <= float(risk.get("max_exposure", 0))),
                ("CONSECUTIVE_LOSS_LIMIT", int(risk.get("consecutive_losses", 0)) < int(risk.get("max_consecutive_losses", 0))),
            ]
            for code, passed in checks:
                if not passed:
                    issues.append({"code": code, "blocking": True, "detail": "daily risk gate failed"})
            daily_risk_ready = all(passed for _, passed in checks)

        health_ready = False
        if health:
            checks = [
                ("DISK_SPACE_LOW", float(health.get("disk_free_mb", 0)) >= float(health.get("minimum_disk_free_mb", 500))),
                ("HEARTBEAT_STALE", int(health.get("heartbeat_age_seconds", 999999)) <= int(health.get("maximum_heartbeat_age_seconds", 300))),
                ("FILESYSTEM_NOT_WRITABLE", bool(health.get("filesystem_writable", False))),
                ("CLOCK_NOT_SYNCHRONIZED", bool(health.get("system_clock_synchronized", False))),
                ("PROCESS_DUPLICATE", int(health.get("runtime_process_count", 0)) <= 1),
            ]
            for code, passed in checks:
                if not passed:
                    issues.append({"code": code, "blocking": True, "detail": "runtime health gate failed"})
            health_ready = all(passed for _, passed in checks)

        blocking = sum(1 for i in issues if i.get("blocking"))
        safe_mode = blocking > 0
        continuous_cycle_ready = bool(
            gates_required and token and market_session_ready and daily_risk_ready and health_ready and not safe_mode
        )

        control_token_written = False
        duplicate_control = False
        if continuous_cycle_ready:
            payload = {
                "stage_range": "V140.02-V140.05",
                "runtime_cycle_id": runtime_cycle_id,
                "market_session_ready": True,
                "daily_risk_ready": True,
                "continuous_cycle_ready": True,
                "runtime_health_ready": True,
                "runtime_control_ready": True,
                "actual_submission_allowed": False,
                "broker_network_allowed": False,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            if control_token_path.exists():
                existing = _load_json(control_token_path)
                if existing.get("runtime_cycle_id") == runtime_cycle_id:
                    duplicate_control = True
                else:
                    issues.append({"code": "CONTROL_TOKEN_CONFLICT", "blocking": True, "detail": "another runtime cycle owns the token"})
            else:
                _atomic_write(control_token_path, payload)
                control_token_written = True

        blocking = sum(1 for i in issues if i.get("blocking"))
        safe_mode = blocking > 0
        runtime_control_ready = bool(
            continuous_cycle_ready and (control_token_written or duplicate_control) and not safe_mode
        )

        if safe_mode:
            state, status = "RUNTIME_CONTROL_SAFE_MODE", "BLOCKED"
        elif runtime_control_ready:
            state, status = "RUNTIME_CONTROL_READY", "PASS"
        else:
            state, status = "WAIT_RUNTIME_READY", "PASS"

        result = {
            "actual_credentials_used": False,
            "actual_external_network_used": False,
            "actual_paper_orders_submitted": 0,
            "blocking_issue_count": blocking,
            "continuous_cycle_ready": continuous_cycle_ready,
            "control_token_path": str(control_token_path.resolve()),
            "control_token_written": control_token_written,
            "daily_risk_ready": daily_risk_ready,
            "duplicate_control": duplicate_control,
            "implementation_type": "ULTRA_FAST_RUNTIME_CONTROL_BUNDLE",
            "issue_count": len(issues),
            "issues": issues,
            "live_orders_submitted": 0,
            "market_phase": market_phase,
            "market_session_ready": market_session_ready,
            "network_requests_executed": 0,
            "next_phase": "V140_06_TO_V140_09" if runtime_control_ready else "V140_02_TO_V140_05_WAIT_RUNTIME_READY",
            "runtime_control_ready": runtime_control_ready,
            "runtime_cycle_id": runtime_cycle_id,
            "runtime_health_ready": health_ready,
            "safe_mode_engaged": safe_mode,
            "stage_range": "V140.02-V140.05",
            "state": state,
            "status": status,
            "validation_mode": "LOCAL_RUNTIME_CONTROL_ONLY",
            "write_requests_executed": 0,
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "result_path": str(result_path.resolve()),
        }
        _atomic_write(result_path, result)
        return result
