from __future__ import annotations

import json
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
    temp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temp.replace(path)


class MultiDayShadowValidation:
    def run(
        self,
        *,
        performance_result_path: Path,
        validation_policy_path: Path,
        multi_day_evidence_path: Path,
        summary_path: Path,
        signal_quality_path: Path,
        risk_consistency_path: Path,
        continuation_decision_path: Path,
        validation_token_path: Path,
        result_path: Path,
    ) -> dict[str, Any]:
        issues: list[dict[str, Any]] = []

        try:
            source = _load(performance_result_path)
        except Exception as exc:
            source = {}
            issues.append({"code":"INVALID_PERFORMANCE_RESULT","blocking":True,"detail":str(exc)})

        if not source:
            issues.append({"code":"PERFORMANCE_RESULT_NOT_FOUND","blocking":True,"detail":str(performance_result_path)})

        source_status = str(source.get("status","")).upper()
        source_state = str(source.get("state","")).upper()
        source_safe = bool(source.get("safe_mode_engaged",False))
        source_ready = bool(source.get("shadow_performance_evaluation_ready",False))
        shadow_session_id = str(source.get("shadow_session_id","")).strip()

        if source_status == "BLOCKED" or source_safe:
            issues.append({"code":"SOURCE_PERFORMANCE_SAFE_MODE","blocking":True,"detail":source_state})

        required = source_ready or source_state == "SHADOW_PERFORMANCE_EVALUATION_READY"

        policy = {}
        evidence = {}
        if required:
            for name,path in (
                ("VALIDATION_POLICY",validation_policy_path),
                ("MULTI_DAY_EVIDENCE",multi_day_evidence_path),
            ):
                try:
                    loaded = _load(path)
                except Exception as exc:
                    loaded = {}
                    issues.append({"code":f"INVALID_{name}","blocking":True,"detail":str(exc)})
                if not loaded:
                    issues.append({"code":f"{name}_NOT_FOUND","blocking":True,"detail":str(path)})
                if name == "VALIDATION_POLICY":
                    policy = loaded
                else:
                    evidence = loaded

        policy_ready = False
        validation_id = ""
        if policy:
            validation_id = str(policy.get("validation_id","")).strip()
            checks = [
                ("VALIDATION_ID_MISSING",bool(validation_id)),
                ("SHADOW_ONLY_REQUIRED",bool(policy.get("shadow_only",False))),
                ("ORDER_SUBMISSION_MUST_BE_DISABLED",not bool(policy.get("order_submission_enabled",True))),
                ("LIVE_TRADING_MUST_BE_DISABLED",not bool(policy.get("live_trading_enabled",True))),
                ("MINIMUM_DAYS_INVALID",int(policy.get("minimum_trading_days",0)) >= 3),
                ("MINIMUM_SIGNALS_INVALID",int(policy.get("minimum_signal_count",0)) >= 1),
                ("MINIMUM_SIGNAL_ACCURACY_INVALID",0 <= float(policy.get("minimum_signal_accuracy_pct",-1)) <= 100),
                ("MINIMUM_RISK_CONSISTENCY_INVALID",0 <= float(policy.get("minimum_risk_consistency_pct",-1)) <= 100),
                ("MAXIMUM_DRAWDOWN_INVALID",0 <= float(policy.get("maximum_drawdown_pct",-1)) <= 100),
            ]
            for code,passed in checks:
                if not passed:
                    issues.append({"code":code,"blocking":True,"detail":"multi-day validation policy gate failed"})
            policy_ready = all(passed for _,passed in checks)

        days = []
        if evidence:
            raw_days = evidence.get("days",[])
            if not isinstance(raw_days,list):
                issues.append({"code":"DAYS_NOT_LIST","blocking":True,"detail":"days must be a list"})
            else:
                days = [item for item in raw_days if isinstance(item,dict)]

        trading_days = len(days)
        total_signals = sum(int(day.get("signal_count",0)) for day in days)
        correct_signals = sum(int(day.get("correct_signal_count",0)) for day in days)
        duplicate_signals = sum(int(day.get("duplicate_signal_count",0)) for day in days)
        late_signals = sum(int(day.get("late_signal_count",0)) for day in days)
        missed_signals = sum(int(day.get("missed_signal_count",0)) for day in days)
        risk_decisions = sum(int(day.get("risk_decision_count",0)) for day in days)
        consistent_risk_decisions = sum(int(day.get("consistent_risk_decision_count",0)) for day in days)
        risk_overrides = sum(int(day.get("risk_override_count",0)) for day in days)
        emergency_stops = sum(int(day.get("emergency_stop_count",0)) for day in days)
        total_pnl = sum(float(day.get("total_pnl",0)) for day in days)
        max_drawdown_pct = max([float(day.get("max_drawdown_pct",0)) for day in days] or [0.0])
        minimum_profit_factor = min([float(day.get("profit_factor",0)) for day in days] or [0.0])

        if required and trading_days < int(policy.get("minimum_trading_days",3)):
            issues.append({"code":"INSUFFICIENT_TRADING_DAYS","blocking":True,"detail":str(trading_days)})
        if required and total_signals < int(policy.get("minimum_signal_count",1)):
            issues.append({"code":"INSUFFICIENT_SIGNAL_COUNT","blocking":True,"detail":str(total_signals)})

        signal_accuracy = (correct_signals / total_signals * 100) if total_signals else 0.0
        risk_consistency = (consistent_risk_decisions / risk_decisions * 100) if risk_decisions else 0.0

        signal_quality_passed = bool(
            total_signals >= int(policy.get("minimum_signal_count",1))
            and signal_accuracy >= float(policy.get("minimum_signal_accuracy_pct",0))
            and duplicate_signals == 0
            and late_signals <= int(policy.get("maximum_late_signals",0))
            and missed_signals <= int(policy.get("maximum_missed_signals",0))
        )
        risk_consistency_passed = bool(
            risk_decisions > 0
            and risk_consistency >= float(policy.get("minimum_risk_consistency_pct",0))
            and risk_overrides <= int(policy.get("maximum_risk_overrides",0))
            and emergency_stops <= int(policy.get("maximum_emergency_stops",0))
        )
        performance_passed = bool(
            max_drawdown_pct <= float(policy.get("maximum_drawdown_pct",100))
            and minimum_profit_factor >= float(policy.get("minimum_profit_factor",0))
        )

        continuation_allowed = bool(
            required and policy_ready
            and trading_days >= int(policy.get("minimum_trading_days",3))
            and total_signals >= int(policy.get("minimum_signal_count",1))
            and signal_quality_passed
            and risk_consistency_passed
            and performance_passed
            and not any(item.get("blocking") for item in issues)
        )

        now = datetime.now(timezone.utc).isoformat()
        summary_written = signal_written = risk_written = decision_written = False
        token_written = duplicate_token = False

        calculation_ready = bool(
            required and policy_ready and days and not any(item.get("blocking") for item in issues)
        )

        if calculation_ready:
            _write(summary_path,{
                "stage":"OP2.09",
                "validation_id":validation_id,
                "shadow_session_id":shadow_session_id,
                "trading_days":trading_days,
                "total_signals":total_signals,
                "total_pnl":round(total_pnl,8),
                "maximum_observed_drawdown_pct":round(max_drawdown_pct,8),
                "minimum_observed_profit_factor":round(minimum_profit_factor,8),
                "created_at":now,
            })
            summary_written = True

            _write(signal_quality_path,{
                "stage":"OP2.10",
                "validation_id":validation_id,
                "signal_accuracy_pct":round(signal_accuracy,8),
                "duplicate_signal_count":duplicate_signals,
                "late_signal_count":late_signals,
                "missed_signal_count":missed_signals,
                "signal_quality_passed":signal_quality_passed,
                "created_at":now,
            })
            signal_written = True

            _write(risk_consistency_path,{
                "stage":"OP2.11",
                "validation_id":validation_id,
                "risk_decision_count":risk_decisions,
                "consistent_risk_decision_count":consistent_risk_decisions,
                "risk_consistency_pct":round(risk_consistency,8),
                "risk_override_count":risk_overrides,
                "emergency_stop_count":emergency_stops,
                "risk_consistency_passed":risk_consistency_passed,
                "created_at":now,
            })
            risk_written = True

            _write(continuation_decision_path,{
                "stage":"OP2.12",
                "validation_id":validation_id,
                "shadow_continuation_allowed":continuation_allowed,
                "decision":"CONTINUE_SHADOW_AUTOMATION" if continuation_allowed else "HOLD_AND_REVIEW",
                "signal_quality_passed":signal_quality_passed,
                "risk_consistency_passed":risk_consistency_passed,
                "performance_passed":performance_passed,
                "shadow_only":True,
                "order_submission_enabled":False,
                "live_trading_enabled":False,
                "created_at":now,
            })
            decision_written = True

            token = {
                "stage_range":"OP2.09-OP2.12",
                "validation_id":validation_id,
                "shadow_session_id":shadow_session_id,
                "multi_day_shadow_validation_ready":True,
                "shadow_continuation_allowed":continuation_allowed,
                "shadow_only":True,
                "order_submission_enabled":False,
                "live_trading_enabled":False,
                "created_at":now,
            }
            if validation_token_path.exists():
                existing = _load(validation_token_path)
                if existing.get("validation_id") == validation_id:
                    duplicate_token = True
                else:
                    issues.append({"code":"VALIDATION_TOKEN_CONFLICT","blocking":True,"detail":"another validation token exists"})
            else:
                _write(validation_token_path,token)
                token_written = True

        blocking = sum(1 for item in issues if item.get("blocking"))
        safe_mode = blocking > 0
        final_ready = bool(
            calculation_ready and summary_written and signal_written and risk_written
            and decision_written and (token_written or duplicate_token) and not safe_mode
        )

        if safe_mode:
            out_state,out_status = "MULTI_DAY_SHADOW_SAFE_MODE","BLOCKED"
        elif final_ready:
            out_state,out_status = "MULTI_DAY_SHADOW_VALIDATION_READY","PASS"
        else:
            out_state,out_status = "WAIT_SHADOW_PERFORMANCE","PASS"

        result = {
            "stage_range":"OP2.09-OP2.12",
            "implementation_type":"MULTI_DAY_SHADOW_VALIDATION",
            "status":out_status,
            "state":out_state,
            "shadow_session_id":shadow_session_id,
            "validation_id":validation_id,
            "policy_ready":policy_ready,
            "trading_days":trading_days,
            "total_signals":total_signals,
            "correct_signals":correct_signals,
            "signal_accuracy_pct":round(signal_accuracy,8),
            "duplicate_signal_count":duplicate_signals,
            "risk_decision_count":risk_decisions,
            "risk_consistency_pct":round(risk_consistency,8),
            "risk_override_count":risk_overrides,
            "emergency_stop_count":emergency_stops,
            "total_pnl":round(total_pnl,8),
            "maximum_observed_drawdown_pct":round(max_drawdown_pct,8),
            "minimum_observed_profit_factor":round(minimum_profit_factor,8),
            "signal_quality_passed":signal_quality_passed,
            "risk_consistency_passed":risk_consistency_passed,
            "performance_passed":performance_passed,
            "shadow_continuation_allowed":continuation_allowed,
            "summary_written":summary_written,
            "signal_quality_written":signal_written,
            "risk_consistency_written":risk_written,
            "continuation_decision_written":decision_written,
            "validation_token_written":token_written,
            "duplicate_validation_token":duplicate_token,
            "multi_day_shadow_validation_ready":final_ready,
            "shadow_only":True,
            "order_submission_enabled":False,
            "broker_write_enabled":False,
            "live_trading_enabled":False,
            "actual_credentials_used":False,
            "actual_external_network_used":False,
            "network_requests_executed":0,
            "write_requests_executed":0,
            "actual_paper_orders_submitted":0,
            "live_orders_submitted":0,
            "safe_mode_engaged":safe_mode,
            "issue_count":len(issues),
            "blocking_issue_count":blocking,
            "issues":issues,
            "next_phase":"OP2_13_AUTOMATIC_SHADOW_SIGNAL_PIPELINE" if final_ready else "OP2_09_TO_OP2_12_WAIT_PERFORMANCE",
            "validation_mode":"LOCAL_MULTI_DAY_SHADOW_ONLY",
            "observed_at":now,
            "result_path":str(result_path.resolve()),
        }
        _write(result_path,result)
        return result
