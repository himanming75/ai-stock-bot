from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


class WeeklyObservationReview:
    def run(
        self,
        *,
        daily_result_path: Path,
        weekly_evidence_path: Path,
        review_policy_path: Path,
        weekly_summary_path: Path,
        alert_report_path: Path,
        stability_score_path: Path,
        continuation_decision_path: Path,
        review_token_path: Path,
        result_path: Path,
    ) -> dict[str, Any]:
        issues: list[dict[str, Any]] = []

        try:
            daily = _load(daily_result_path)
        except Exception as exc:
            daily = {}
            issues.append({"code":"INVALID_DAILY_RESULT","blocking":True,"detail":str(exc)})

        if not daily:
            issues.append({"code":"DAILY_RESULT_NOT_FOUND","blocking":True,"detail":str(daily_result_path)})

        daily_status = str(daily.get("status","")).upper()
        daily_state = str(daily.get("state","")).upper()
        daily_safe = bool(daily.get("safe_mode_engaged",False))
        daily_ready = bool(daily.get("daily_read_only_observation_ready",False))
        pilot_id = str(daily.get("pilot_id","")).strip()

        if daily_status == "BLOCKED" or daily_safe:
            issues.append({"code":"SOURCE_DAILY_OBSERVATION_SAFE_MODE","blocking":True,"detail":daily_state})

        required = daily_ready or daily_state == "DAILY_READ_ONLY_OBSERVATION_READY"

        evidence = {}
        policy = {}
        if required:
            for name,path in (("WEEKLY_EVIDENCE",weekly_evidence_path),("REVIEW_POLICY",review_policy_path)):
                try:
                    loaded = _load(path)
                except Exception as exc:
                    loaded = {}
                    issues.append({"code":f"INVALID_{name}","blocking":True,"detail":str(exc)})
                if not loaded:
                    issues.append({"code":f"{name}_NOT_FOUND","blocking":True,"detail":str(path)})
                if name=="WEEKLY_EVIDENCE":
                    evidence=loaded
                else:
                    policy=loaded

        policy_ready=False
        review_id=""
        if policy:
            review_id=str(policy.get("review_id","")).strip()
            checks=[
                ("REVIEW_ID_MISSING",bool(review_id)),
                ("READ_ONLY_REQUIRED",bool(policy.get("read_only",False))),
                ("ORDER_SUBMISSION_MUST_BE_DISABLED",not bool(policy.get("order_submission_enabled",True))),
                ("LIVE_TRADING_MUST_BE_DISABLED",not bool(policy.get("live_trading_enabled",True))),
                ("MINIMUM_DAYS_INVALID",int(policy.get("minimum_observation_days",0))>=5),
                ("MINIMUM_SCORE_INVALID",0<=int(policy.get("minimum_stability_score",0))<=100),
            ]
            for code,passed in checks:
                if not passed:
                    issues.append({"code":code,"blocking":True,"detail":"weekly review policy gate failed"})
            policy_ready=all(passed for _,passed in checks)

        weekly_ready=False
        alerts=[]
        score=0
        continuation_allowed=False
        observation_days=0
        if evidence:
            days=list(evidence.get("days",[]))
            observation_days=len(days)
            if observation_days < int(policy.get("minimum_observation_days",5)):
                issues.append({"code":"INSUFFICIENT_OBSERVATION_DAYS","blocking":True,"detail":str(observation_days)})
            total_network_failures=0
            total_snapshot_failures=0
            total_unexpected_orders=0
            total_unexpected_positions=0
            total_risk_violations=0
            total_blocked_accounts=0
            total_trading_blocks=0
            max_abs_equity_drift=0.0
            max_abs_cash_drift=0.0

            for index,item in enumerate(days, start=1):
                if not isinstance(item,dict):
                    alerts.append({"severity":"CRITICAL","code":"INVALID_DAY_RECORD","day_index":index})
                    continue
                total_network_failures += int(item.get("network_failures",0))
                total_snapshot_failures += int(item.get("snapshot_failures",0))
                total_unexpected_orders += int(item.get("unexpected_orders",0))
                total_unexpected_positions += int(item.get("unexpected_positions",0))
                total_risk_violations += int(item.get("risk_violations",0))
                total_blocked_accounts += int(item.get("account_blocked_events",0))
                total_trading_blocks += int(item.get("trading_blocked_events",0))
                max_abs_equity_drift=max(max_abs_equity_drift,abs(float(item.get("equity_drift",0))))
                max_abs_cash_drift=max(max_abs_cash_drift,abs(float(item.get("cash_drift",0))))

            def add_alert(condition, severity, code, count):
                if condition:
                    alerts.append({"severity":severity,"code":code,"count":count})

            add_alert(total_network_failures>0,"WARNING","NETWORK_FAILURES",total_network_failures)
            add_alert(total_snapshot_failures>0,"WARNING","SNAPSHOT_FAILURES",total_snapshot_failures)
            add_alert(total_unexpected_orders>0,"CRITICAL","UNEXPECTED_ORDERS",total_unexpected_orders)
            add_alert(total_unexpected_positions>0,"CRITICAL","UNEXPECTED_POSITIONS",total_unexpected_positions)
            add_alert(total_risk_violations>0,"CRITICAL","RISK_VIOLATIONS",total_risk_violations)
            add_alert(total_blocked_accounts>0,"CRITICAL","ACCOUNT_BLOCKED_EVENTS",total_blocked_accounts)
            add_alert(total_trading_blocks>0,"CRITICAL","TRADING_BLOCKED_EVENTS",total_trading_blocks)

            score=100
            score -= min(20,total_network_failures*5)
            score -= min(20,total_snapshot_failures*5)
            score -= min(30,total_unexpected_orders*15)
            score -= min(30,total_unexpected_positions*15)
            score -= min(40,total_risk_violations*20)
            score -= min(50,total_blocked_accounts*25)
            score -= min(50,total_trading_blocks*25)
            if max_abs_equity_drift > float(policy.get("max_abs_equity_drift",0)):
                score -= 10
                alerts.append({"severity":"WARNING","code":"EQUITY_DRIFT_THRESHOLD_EXCEEDED","value":max_abs_equity_drift})
            if max_abs_cash_drift > float(policy.get("max_abs_cash_drift",0)):
                score -= 10
                alerts.append({"severity":"WARNING","code":"CASH_DRIFT_THRESHOLD_EXCEEDED","value":max_abs_cash_drift})
            score=max(0,min(100,score))

            critical_count=sum(1 for alert in alerts if alert["severity"]=="CRITICAL")
            continuation_allowed=(
                observation_days>=int(policy.get("minimum_observation_days",5))
                and score>=int(policy.get("minimum_stability_score",90))
                and critical_count==0
            )
            weekly_ready=observation_days>=int(policy.get("minimum_observation_days",5))

        now=datetime.now(timezone.utc).isoformat()
        summary_written=alert_written=score_written=decision_written=False
        token_written=duplicate_token=False

        if required and evidence:
            _write(weekly_summary_path,{
                "stage":"OP1.09","pilot_id":pilot_id,"review_id":review_id,
                "observation_days":observation_days,"weekly_summary_ready":weekly_ready,
                "created_at":now})
            summary_written=True
            _write(alert_report_path,{
                "stage":"OP1.10","pilot_id":pilot_id,"review_id":review_id,
                "alert_count":len(alerts),"alerts":alerts,"created_at":now})
            alert_written=True
            _write(stability_score_path,{
                "stage":"OP1.11","pilot_id":pilot_id,"review_id":review_id,
                "stability_score":score,"minimum_required":int(policy.get("minimum_stability_score",90)),
                "created_at":now})
            score_written=True
            _write(continuation_decision_path,{
                "stage":"OP1.12","pilot_id":pilot_id,"review_id":review_id,
                "pilot_continuation_allowed":continuation_allowed,
                "decision":"CONTINUE_READ_ONLY_PILOT" if continuation_allowed else "HOLD_AND_REVIEW",
                "read_only":True,"order_submission_enabled":False,"live_trading_enabled":False,
                "created_at":now})
            decision_written=True

        review_ready=bool(required and policy_ready and weekly_ready and continuation_allowed and not any(i.get("blocking") for i in issues))

        if review_ready:
            token={
                "stage_range":"OP1.09-OP1.12","pilot_id":pilot_id,"review_id":review_id,
                "weekly_review_ready":True,"pilot_continuation_allowed":True,
                "read_only":True,"order_submission_enabled":False,"live_trading_enabled":False,
                "created_at":now}
            if review_token_path.exists():
                existing=_load(review_token_path)
                if existing.get("pilot_id")==pilot_id and existing.get("review_id")==review_id:
                    duplicate_token=True
                else:
                    issues.append({"code":"WEEKLY_REVIEW_TOKEN_CONFLICT","blocking":True,"detail":"another review token exists"})
            else:
                _write(review_token_path,token)
                token_written=True

        blocking=sum(1 for i in issues if i.get("blocking"))
        safe_mode=blocking>0
        final_ready=bool(review_ready and summary_written and alert_written and score_written and decision_written and (token_written or duplicate_token) and not safe_mode)

        if safe_mode:
            state,status="WEEKLY_OBSERVATION_SAFE_MODE","BLOCKED"
        elif final_ready:
            state,status="WEEKLY_PILOT_REVIEW_READY","PASS"
        else:
            state,status="WAIT_DAILY_READ_ONLY_OBSERVATION","PASS"

        result={
            "stage_range":"OP1.09-OP1.12",
            "implementation_type":"WEEKLY_OBSERVATION_REVIEW",
            "status":status,"state":state,
            "pilot_id":pilot_id,"review_id":review_id,
            "observation_days":observation_days,
            "weekly_summary_ready":weekly_ready,
            "alert_count":len(alerts),
            "stability_score":score,
            "pilot_continuation_allowed":continuation_allowed,
            "weekly_review_ready":final_ready,
            "summary_written":summary_written,
            "alert_report_written":alert_written,
            "stability_score_written":score_written,
            "continuation_decision_written":decision_written,
            "review_token_written":token_written,
            "duplicate_review_token":duplicate_token,
            "read_only":True,
            "order_submission_enabled":False,
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
            "next_phase":"OP1_13_AUTOMATIC_SNAPSHOT_COLLECTION" if final_ready else "OP1_09_TO_OP1_12_WAIT_DAILY_OBSERVATION",
            "validation_mode":"LOCAL_WEEKLY_OBSERVATION_REVIEW_ONLY",
            "observed_at":now,
            "result_path":str(result_path.resolve()),
        }
        _write(result_path,result)
        return result
