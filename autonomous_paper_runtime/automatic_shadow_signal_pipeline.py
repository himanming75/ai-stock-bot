from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


VALID_ACTIONS = {"BUY", "SELL", "HOLD"}


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


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(payload, sort_keys=True) + "\n")


def _signal_id(pipeline_id: str, symbol: str, action: str, as_of: str) -> str:
    raw = f"{pipeline_id}|{symbol}|{action}|{as_of}"
    return "auto-shadow-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


class AutomaticShadowSignalPipeline:
    def run(
        self,
        *,
        validation_result_path: Path,
        pipeline_policy_path: Path,
        market_snapshot_path: Path,
        strategy_snapshot_path: Path,
        generated_signal_path: Path,
        signal_queue_path: Path,
        validation_report_path: Path,
        handoff_token_path: Path,
        result_path: Path,
    ) -> dict[str, Any]:
        issues: list[dict[str, Any]] = []

        try:
            source = _load(validation_result_path)
        except Exception as exc:
            source = {}
            issues.append({"code":"INVALID_MULTI_DAY_VALIDATION_RESULT","blocking":True,"detail":str(exc)})

        if not source:
            issues.append({"code":"MULTI_DAY_VALIDATION_RESULT_NOT_FOUND","blocking":True,"detail":str(validation_result_path)})

        source_status = str(source.get("status","")).upper()
        source_state = str(source.get("state","")).upper()
        source_safe = bool(source.get("safe_mode_engaged",False))
        source_ready = bool(source.get("multi_day_shadow_validation_ready",False))
        continuation_allowed = bool(source.get("shadow_continuation_allowed",False))
        shadow_session_id = str(source.get("shadow_session_id","")).strip()

        if source_status == "BLOCKED" or source_safe:
            issues.append({"code":"SOURCE_MULTI_DAY_SAFE_MODE","blocking":True,"detail":source_state})

        required = (
            (source_ready and continuation_allowed)
            or source_state == "MULTI_DAY_SHADOW_VALIDATION_READY"
        )

        policy = {}
        market = {}
        strategy = {}

        if required:
            for name,path in (
                ("PIPELINE_POLICY",pipeline_policy_path),
                ("MARKET_SNAPSHOT",market_snapshot_path),
                ("STRATEGY_SNAPSHOT",strategy_snapshot_path),
            ):
                try:
                    loaded = _load(path)
                except Exception as exc:
                    loaded = {}
                    issues.append({"code":f"INVALID_{name}","blocking":True,"detail":str(exc)})
                if not loaded:
                    issues.append({"code":f"{name}_NOT_FOUND","blocking":True,"detail":str(path)})
                if name == "PIPELINE_POLICY":
                    policy = loaded
                elif name == "MARKET_SNAPSHOT":
                    market = loaded
                else:
                    strategy = loaded

        policy_ready = False
        pipeline_id = ""
        if policy:
            pipeline_id = str(policy.get("pipeline_id","")).strip()
            checks = [
                ("PIPELINE_ID_MISSING",bool(pipeline_id)),
                ("SHADOW_ONLY_REQUIRED",bool(policy.get("shadow_only",False))),
                ("ORDER_SUBMISSION_MUST_BE_DISABLED",not bool(policy.get("order_submission_enabled",True))),
                ("BROKER_WRITE_MUST_BE_DISABLED",not bool(policy.get("broker_write_enabled",True))),
                ("LIVE_TRADING_MUST_BE_DISABLED",not bool(policy.get("live_trading_enabled",True))),
                ("MAX_QUEUE_SIZE_INVALID",1 <= int(policy.get("max_queue_size",0)) <= 1000),
                ("MIN_CONFIDENCE_INVALID",0 <= float(policy.get("minimum_confidence",-1)) <= 1),
                ("ALLOWED_ACTIONS_INVALID",set(policy.get("allowed_actions",[])) == VALID_ACTIONS),
            ]
            for code,passed in checks:
                if not passed:
                    issues.append({"code":code,"blocking":True,"detail":"pipeline policy gate failed"})
            policy_ready = all(passed for _,passed in checks)

        market_ready = False
        symbol = ""
        reference_price = 0.0
        market_open = False
        as_of = ""
        if market:
            symbol = str(market.get("symbol","")).upper().strip()
            reference_price = float(market.get("reference_price",0))
            market_open = bool(market.get("market_open",False))
            as_of = str(market.get("as_of","")).strip()
            checks = [
                ("MARKET_SYMBOL_MISSING",bool(symbol)),
                ("INVALID_REFERENCE_PRICE",reference_price > 0),
                ("MARKET_TIMESTAMP_MISSING",bool(as_of)),
                ("MARKET_SNAPSHOT_STALE",not bool(market.get("stale",True))),
            ]
            for code,passed in checks:
                if not passed:
                    issues.append({"code":code,"blocking":True,"detail":"market snapshot validation failed"})
            market_ready = all(passed for _,passed in checks)

        strategy_ready = False
        raw_action = ""
        confidence = 0.0
        quantity = 0
        if strategy:
            raw_action = str(strategy.get("action","")).upper().strip()
            confidence = float(strategy.get("confidence",0))
            quantity = int(strategy.get("quantity",0))
            checks = [
                ("INVALID_STRATEGY_ACTION",raw_action in VALID_ACTIONS),
                ("INVALID_STRATEGY_CONFIDENCE",0 <= confidence <= 1),
                ("INVALID_STRATEGY_QUANTITY",quantity >= 0),
                ("STRATEGY_NOT_VERIFIED",bool(strategy.get("strategy_verified",False))),
            ]
            for code,passed in checks:
                if not passed:
                    issues.append({"code":code,"blocking":True,"detail":"strategy snapshot validation failed"})
            strategy_ready = all(passed for _,passed in checks)

        approved_action = "HOLD"
        approved_quantity = 0
        pipeline_reasons: list[str] = []

        if policy_ready and market_ready and strategy_ready:
            if not market_open:
                pipeline_reasons.append("MARKET_CLOSED")
            if confidence < float(policy["minimum_confidence"]):
                pipeline_reasons.append("CONFIDENCE_BELOW_MINIMUM")
            if raw_action in {"BUY","SELL"} and quantity <= 0:
                pipeline_reasons.append("ZERO_QUANTITY")

            if not pipeline_reasons:
                approved_action = raw_action
                approved_quantity = quantity if raw_action != "HOLD" else 0

        signal_id = ""
        generated_written = False
        queue_written = False
        validation_written = False
        token_written = False
        duplicate_signal = False
        duplicate_token = False

        queue_records: list[dict[str, Any]] = []
        if signal_queue_path.exists():
            for line in signal_queue_path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    item = json.loads(line)
                    if isinstance(item,dict):
                        queue_records.append(item)

        blocking_before_generation = sum(1 for i in issues if i.get("blocking"))
        generation_ready = bool(
            required and policy_ready and market_ready and strategy_ready
            and blocking_before_generation == 0
        )

        now = datetime.now(timezone.utc).isoformat()

        if generation_ready:
            signal_id = _signal_id(pipeline_id,symbol,raw_action,as_of)
            duplicate_signal = any(item.get("signal_id") == signal_id for item in queue_records)
            if duplicate_signal:
                issues.append({"code":"DUPLICATE_AUTOMATIC_SHADOW_SIGNAL","blocking":True,"detail":signal_id})
            elif len(queue_records) >= int(policy["max_queue_size"]):
                issues.append({"code":"SHADOW_SIGNAL_QUEUE_FULL","blocking":True,"detail":str(len(queue_records))})
            else:
                generated = {
                    "stage":"OP2.13",
                    "signal_id":signal_id,
                    "pipeline_id":pipeline_id,
                    "shadow_session_id":shadow_session_id,
                    "symbol":symbol,
                    "requested_action":raw_action,
                    "approved_action":approved_action,
                    "confidence":confidence,
                    "reference_price":reference_price,
                    "requested_quantity":quantity,
                    "approved_quantity":approved_quantity,
                    "pipeline_reasons":pipeline_reasons,
                    "shadow_only":True,
                    "order_submission_attempted":False,
                    "created_at":now,
                }
                _write(generated_signal_path,generated)
                generated_written = True

                _append_jsonl(signal_queue_path,{
                    "stage":"OP2.14",
                    "signal_id":signal_id,
                    "pipeline_id":pipeline_id,
                    "symbol":symbol,
                    "action":approved_action,
                    "quantity":approved_quantity,
                    "confidence":confidence,
                    "status":"QUEUED_FOR_SHADOW_DECISION",
                    "shadow_only":True,
                    "created_at":now,
                })
                queue_written = True

                _write(validation_report_path,{
                    "stage":"OP2.15",
                    "signal_id":signal_id,
                    "market_ready":market_ready,
                    "strategy_ready":strategy_ready,
                    "policy_ready":policy_ready,
                    "pipeline_validated":True,
                    "approved_action":approved_action,
                    "pipeline_reasons":pipeline_reasons,
                    "created_at":now,
                })
                validation_written = True

                token = {
                    "stage":"OP2.16",
                    "signal_id":signal_id,
                    "pipeline_id":pipeline_id,
                    "automatic_shadow_signal_pipeline_ready":True,
                    "shadow_decision_handoff_ready":True,
                    "approved_action":approved_action,
                    "order_submission_enabled":False,
                    "broker_write_enabled":False,
                    "live_trading_enabled":False,
                    "created_at":now,
                }
                if handoff_token_path.exists():
                    existing = _load(handoff_token_path)
                    if existing.get("signal_id") == signal_id:
                        duplicate_token = True
                    else:
                        issues.append({"code":"SHADOW_HANDOFF_TOKEN_CONFLICT","blocking":True,"detail":"another signal owns the token"})
                else:
                    _write(handoff_token_path,token)
                    token_written = True

        blocking = sum(1 for i in issues if i.get("blocking"))
        safe_mode = blocking > 0
        final_ready = bool(
            generation_ready and not duplicate_signal and generated_written
            and queue_written and validation_written
            and (token_written or duplicate_token) and not safe_mode
        )

        if safe_mode:
            out_state,out_status = "AUTOMATIC_SHADOW_PIPELINE_SAFE_MODE","BLOCKED"
        elif final_ready:
            out_state,out_status = "AUTOMATIC_SHADOW_SIGNAL_PIPELINE_READY","PASS"
        else:
            out_state,out_status = "WAIT_MULTI_DAY_SHADOW_VALIDATION","PASS"

        result = {
            "stage_range":"OP2.13-OP2.16",
            "implementation_type":"AUTOMATIC_SHADOW_SIGNAL_PIPELINE",
            "status":out_status,
            "state":out_state,
            "shadow_session_id":shadow_session_id,
            "pipeline_id":pipeline_id,
            "signal_id":signal_id,
            "symbol":symbol,
            "requested_action":raw_action,
            "approved_action":approved_action,
            "confidence":confidence,
            "requested_quantity":quantity,
            "approved_quantity":approved_quantity,
            "pipeline_reasons":pipeline_reasons,
            "policy_ready":policy_ready,
            "market_ready":market_ready,
            "strategy_ready":strategy_ready,
            "duplicate_signal":duplicate_signal,
            "generated_signal_written":generated_written,
            "signal_queue_written":queue_written,
            "validation_report_written":validation_written,
            "handoff_token_written":token_written,
            "duplicate_handoff_token":duplicate_token,
            "automatic_shadow_signal_pipeline_ready":final_ready,
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
            "next_phase":"OP2_17_SHADOW_DAILY_AUTOMATION" if final_ready else "OP2_13_TO_OP2_16_WAIT_VALIDATION",
            "validation_mode":"LOCAL_AUTOMATIC_SHADOW_PIPELINE_ONLY",
            "observed_at":now,
            "result_path":str(result_path.resolve()),
        }
        _write(result_path,result)
        return result
