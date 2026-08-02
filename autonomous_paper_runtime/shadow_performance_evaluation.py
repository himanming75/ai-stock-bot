from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON object required: {path}")
    return payload


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temp.replace(path)


class ShadowPerformanceEvaluation:
    def run(
        self,
        *,
        shadow_result_path: Path,
        evaluation_policy_path: Path,
        trade_evidence_path: Path,
        trade_metrics_path: Path,
        equity_curve_path: Path,
        performance_report_path: Path,
        evaluation_token_path: Path,
        result_path: Path,
    ) -> dict[str, Any]:
        issues: list[dict[str, Any]] = []

        try:
            source = _load(shadow_result_path)
        except Exception as exc:
            source = {}
            issues.append({
                "code": "INVALID_SHADOW_RESULT",
                "blocking": True,
                "detail": str(exc),
            })

        if not source:
            issues.append({
                "code": "SHADOW_RESULT_NOT_FOUND",
                "blocking": True,
                "detail": str(shadow_result_path),
            })

        source_status = str(source.get("status", "")).upper()
        source_state = str(source.get("state", "")).upper()
        source_safe = bool(source.get("safe_mode_engaged", False))
        source_ready = bool(source.get("shadow_decision_ready", False))
        shadow_session_id = str(
            source.get("shadow_session_id", "")
        ).strip()

        if source_status == "BLOCKED" or source_safe:
            issues.append({
                "code": "SOURCE_SHADOW_SAFE_MODE",
                "blocking": True,
                "detail": source_state,
            })

        required = source_ready or source_state == "SHADOW_DECISION_READY"

        policy: dict[str, Any] = {}
        evidence: dict[str, Any] = {}

        if required:
            for name, path in (
                ("EVALUATION_POLICY", evaluation_policy_path),
                ("TRADE_EVIDENCE", trade_evidence_path),
            ):
                try:
                    loaded = _load(path)
                except Exception as exc:
                    loaded = {}
                    issues.append({
                        "code": f"INVALID_{name}",
                        "blocking": True,
                        "detail": str(exc),
                    })

                if not loaded:
                    issues.append({
                        "code": f"{name}_NOT_FOUND",
                        "blocking": True,
                        "detail": str(path),
                    })

                if name == "EVALUATION_POLICY":
                    policy = loaded
                else:
                    evidence = loaded

        policy_ready = False
        evaluation_id = ""
        if policy:
            evaluation_id = str(
                policy.get("evaluation_id", "")
            ).strip()
            checks = [
                ("EVALUATION_ID_MISSING", bool(evaluation_id)),
                ("SHADOW_ONLY_REQUIRED", bool(policy.get("shadow_only", False))),
                (
                    "ORDER_SUBMISSION_MUST_BE_DISABLED",
                    not bool(policy.get("order_submission_enabled", True)),
                ),
                (
                    "LIVE_TRADING_MUST_BE_DISABLED",
                    not bool(policy.get("live_trading_enabled", True)),
                ),
                (
                    "MINIMUM_TRADES_INVALID",
                    int(policy.get("minimum_completed_trades", 0)) >= 1,
                ),
                (
                    "MAX_DRAWDOWN_LIMIT_INVALID",
                    0 <= float(policy.get("maximum_drawdown_limit_pct", -1)) <= 100,
                ),
                (
                    "MINIMUM_PROFIT_FACTOR_INVALID",
                    float(policy.get("minimum_profit_factor", -1)) >= 0,
                ),
            ]
            for code, passed in checks:
                if not passed:
                    issues.append({
                        "code": code,
                        "blocking": True,
                        "detail": "evaluation policy gate failed",
                    })
            policy_ready = all(passed for _, passed in checks)

        trades: list[dict[str, Any]] = []
        evidence_ready = False
        if evidence:
            raw_trades = evidence.get("trades", [])
            if not isinstance(raw_trades, list):
                issues.append({
                    "code": "TRADES_NOT_LIST",
                    "blocking": True,
                    "detail": "trades must be a list",
                })
            else:
                for index, item in enumerate(raw_trades, start=1):
                    if not isinstance(item, dict):
                        issues.append({
                            "code": "INVALID_TRADE_RECORD",
                            "blocking": True,
                            "detail": f"index={index}",
                        })
                        continue
                    action = str(item.get("action", "")).upper()
                    entry = float(item.get("entry_price", 0))
                    exit_price = float(item.get("exit_price", 0))
                    quantity = int(item.get("quantity", 0))
                    checks = [
                        action in {"BUY", "SELL"},
                        entry > 0,
                        exit_price > 0,
                        quantity > 0,
                        bool(str(item.get("decision_id", "")).strip()),
                    ]
                    if not all(checks):
                        issues.append({
                            "code": "INVALID_COMPLETED_TRADE",
                            "blocking": True,
                            "detail": f"index={index}",
                        })
                        continue
                    trades.append(item)

                if len(trades) < int(policy.get("minimum_completed_trades", 1)):
                    issues.append({
                        "code": "INSUFFICIENT_COMPLETED_TRADES",
                        "blocking": True,
                        "detail": str(len(trades)),
                    })
                evidence_ready = len(trades) >= int(
                    policy.get("minimum_completed_trades", 1)
                )

        pnl_values: list[float] = []
        trade_rows: list[dict[str, Any]] = []
        equity_curve: list[dict[str, Any]] = []
        total_pnl = 0.0
        gross_profit = 0.0
        gross_loss = 0.0
        wins = 0
        losses = 0
        peak = 0.0
        max_drawdown = 0.0

        if evidence_ready and not any(i.get("blocking") for i in issues):
            for index, trade in enumerate(trades, start=1):
                action = str(trade["action"]).upper()
                entry = float(trade["entry_price"])
                exit_price = float(trade["exit_price"])
                quantity = int(trade["quantity"])
                fees = float(trade.get("fees", 0))

                raw = (
                    (exit_price - entry) * quantity
                    if action == "BUY"
                    else (entry - exit_price) * quantity
                )
                pnl = raw - fees
                pnl_values.append(pnl)
                total_pnl += pnl

                if pnl > 0:
                    wins += 1
                    gross_profit += pnl
                elif pnl < 0:
                    losses += 1
                    gross_loss += abs(pnl)

                peak = max(peak, total_pnl)
                drawdown = peak - total_pnl
                max_drawdown = max(max_drawdown, drawdown)

                trade_rows.append({
                    "decision_id": trade["decision_id"],
                    "symbol": str(trade.get("symbol", "")).upper(),
                    "action": action,
                    "entry_price": entry,
                    "exit_price": exit_price,
                    "quantity": quantity,
                    "fees": fees,
                    "pnl": round(pnl, 8),
                    "profitable": pnl > 0,
                })
                equity_curve.append({
                    "trade_number": index,
                    "decision_id": trade["decision_id"],
                    "cumulative_pnl": round(total_pnl, 8),
                    "drawdown": round(drawdown, 8),
                })

        trade_count = len(pnl_values)
        win_rate = (wins / trade_count * 100) if trade_count else 0.0
        average_pnl = (total_pnl / trade_count) if trade_count else 0.0
        profit_factor = (
            gross_profit / gross_loss
            if gross_loss > 0
            else (999.0 if gross_profit > 0 else 0.0)
        )

        initial_shadow_capital = float(
            policy.get("initial_shadow_capital", 100000)
        ) if policy else 100000.0
        max_drawdown_pct = (
            max_drawdown / initial_shadow_capital * 100
            if initial_shadow_capital > 0
            else 0.0
        )

        mean = average_pnl
        variance = (
            sum((value - mean) ** 2 for value in pnl_values) / trade_count
            if trade_count
            else 0.0
        )
        stddev = math.sqrt(variance)
        shadow_sharpe = (
            mean / stddev * math.sqrt(trade_count)
            if stddev > 0 and trade_count > 0
            else 0.0
        )

        performance_approved = bool(
            evidence_ready
            and max_drawdown_pct
            <= float(policy.get("maximum_drawdown_limit_pct", 100))
            and profit_factor
            >= float(policy.get("minimum_profit_factor", 0))
        )

        now = datetime.now(timezone.utc).isoformat()
        metrics_written = curve_written = report_written = False
        token_written = duplicate_token = False

        calculation_ready = bool(
            required
            and policy_ready
            and evidence_ready
            and not any(i.get("blocking") for i in issues)
        )

        if calculation_ready:
            _write(trade_metrics_path, {
                "stage": "OP2.05",
                "evaluation_id": evaluation_id,
                "shadow_session_id": shadow_session_id,
                "completed_trade_count": trade_count,
                "wins": wins,
                "losses": losses,
                "win_rate_pct": round(win_rate, 8),
                "total_pnl": round(total_pnl, 8),
                "average_pnl": round(average_pnl, 8),
                "gross_profit": round(gross_profit, 8),
                "gross_loss": round(gross_loss, 8),
                "profit_factor": round(profit_factor, 8),
                "trades": trade_rows,
                "created_at": now,
            })
            metrics_written = True

            _write(equity_curve_path, {
                "stage": "OP2.06",
                "evaluation_id": evaluation_id,
                "initial_shadow_capital": initial_shadow_capital,
                "max_drawdown": round(max_drawdown, 8),
                "max_drawdown_pct": round(max_drawdown_pct, 8),
                "shadow_sharpe": round(shadow_sharpe, 8),
                "equity_curve": equity_curve,
                "created_at": now,
            })
            curve_written = True

            _write(performance_report_path, {
                "stage": "OP2.07",
                "evaluation_id": evaluation_id,
                "completed_trade_count": trade_count,
                "win_rate_pct": round(win_rate, 8),
                "profit_factor": round(profit_factor, 8),
                "max_drawdown_pct": round(max_drawdown_pct, 8),
                "shadow_sharpe": round(shadow_sharpe, 8),
                "performance_approved": performance_approved,
                "decision": (
                    "CONTINUE_SHADOW_EVALUATION"
                    if performance_approved
                    else "HOLD_AND_REVIEW"
                ),
                "shadow_only": True,
                "order_submission_enabled": False,
                "live_trading_enabled": False,
                "created_at": now,
            })
            report_written = True

            token = {
                "stage": "OP2.08",
                "evaluation_id": evaluation_id,
                "shadow_session_id": shadow_session_id,
                "shadow_performance_evaluation_ready": True,
                "performance_approved": performance_approved,
                "shadow_only": True,
                "order_submission_enabled": False,
                "live_trading_enabled": False,
                "created_at": now,
            }
            if evaluation_token_path.exists():
                existing = _load(evaluation_token_path)
                if existing.get("evaluation_id") == evaluation_id:
                    duplicate_token = True
                else:
                    issues.append({
                        "code": "EVALUATION_TOKEN_CONFLICT",
                        "blocking": True,
                        "detail": "another evaluation token exists",
                    })
            else:
                _write(evaluation_token_path, token)
                token_written = True

        blocking = sum(1 for issue in issues if issue.get("blocking"))
        safe_mode = blocking > 0
        final_ready = bool(
            calculation_ready
            and metrics_written
            and curve_written
            and report_written
            and (token_written or duplicate_token)
            and not safe_mode
        )

        if safe_mode:
            state, status = "SHADOW_PERFORMANCE_SAFE_MODE", "BLOCKED"
        elif final_ready:
            state, status = "SHADOW_PERFORMANCE_EVALUATION_READY", "PASS"
        else:
            state, status = "WAIT_SHADOW_DECISION", "PASS"

        result = {
            "stage_range": "OP2.05-OP2.08",
            "implementation_type": "SHADOW_PERFORMANCE_EVALUATION",
            "status": status,
            "state": state,
            "shadow_session_id": shadow_session_id,
            "evaluation_id": evaluation_id,
            "policy_ready": policy_ready,
            "evidence_ready": evidence_ready,
            "completed_trade_count": trade_count,
            "wins": wins,
            "losses": losses,
            "win_rate_pct": round(win_rate, 8),
            "total_pnl": round(total_pnl, 8),
            "average_pnl": round(average_pnl, 8),
            "profit_factor": round(profit_factor, 8),
            "max_drawdown": round(max_drawdown, 8),
            "max_drawdown_pct": round(max_drawdown_pct, 8),
            "shadow_sharpe": round(shadow_sharpe, 8),
            "performance_approved": performance_approved,
            "trade_metrics_written": metrics_written,
            "equity_curve_written": curve_written,
            "performance_report_written": report_written,
            "evaluation_token_written": token_written,
            "duplicate_evaluation_token": duplicate_token,
            "shadow_performance_evaluation_ready": final_ready,
            "shadow_only": True,
            "order_submission_enabled": False,
            "broker_write_enabled": False,
            "live_trading_enabled": False,
            "actual_credentials_used": False,
            "actual_external_network_used": False,
            "network_requests_executed": 0,
            "write_requests_executed": 0,
            "actual_paper_orders_submitted": 0,
            "live_orders_submitted": 0,
            "safe_mode_engaged": safe_mode,
            "issue_count": len(issues),
            "blocking_issue_count": blocking,
            "issues": issues,
            "next_phase": (
                "OP2_09_SHADOW_MULTI_DAY_VALIDATION"
                if final_ready
                else "OP2_05_TO_OP2_08_WAIT_SHADOW_DECISION"
            ),
            "validation_mode": "LOCAL_SHADOW_PERFORMANCE_ONLY",
            "observed_at": now,
            "result_path": str(result_path.resolve()),
        }
        _write(result_path, result)
        return result
