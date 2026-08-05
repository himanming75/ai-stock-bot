from __future__ import annotations
from typing import Any


class ControlPolicyEngine:
    def evaluate(self, request: dict[str, Any]) -> dict[str, Any]:
        request_type = request["request_type"]
        value = request.get("proposed_value", {})
        blockers = []

        if request_type == "STRATEGY_WEIGHT_CHANGE":
            weight = float(value.get("weight", -1))
            if weight < 0 or weight > 1:
                blockers.append("STRATEGY_WEIGHT_OUT_OF_RANGE")

        if request_type == "WORKER_SCALE_CHANGE":
            workers = int(value.get("worker_count", 0))
            if workers < 1 or workers > 16:
                blockers.append("WORKER_COUNT_OUT_OF_RANGE")

        if request_type == "SCHEDULER_CHANGE":
            interval = int(value.get("interval_seconds", 0))
            if interval < 10 or interval > 86400:
                blockers.append("SCHEDULER_INTERVAL_OUT_OF_RANGE")

        if request_type == "RUNTIME_STATE_CHANGE":
            if value.get("target_state") not in {
                "START_PREVIEW",
                "STOP_PREVIEW",
                "PAUSE_PREVIEW",
            }:
                blockers.append("INVALID_RUNTIME_TARGET")

        if request_type == "STRATEGY_STATE_CHANGE":
            if value.get("target_state") not in {
                "ENABLE_PREVIEW",
                "DISABLE_PREVIEW",
            }:
                blockers.append("INVALID_STRATEGY_TARGET")

        if request_type == "KILL_SWITCH_CHANGE":
            if value.get("target_state") not in {
                "ACTIVATE_PREVIEW",
                "DEACTIVATE_PREVIEW",
            }:
                blockers.append("INVALID_KILL_SWITCH_TARGET")

        if request_type == "EMERGENCY_STOP_REQUEST":
            if value.get("target_state") != "ACTIVATE_PREVIEW":
                blockers.append("EMERGENCY_STOP_MUST_ACTIVATE")

        if value.get("broker_mode") == "live":
            blockers.append("LIVE_BROKER_MODE_REJECTED")
        if value.get("write_enabled") is True:
            blockers.append("BROKER_WRITE_ENABLE_REJECTED")
        if value.get("automatic_order_submission_enabled") is True:
            blockers.append("AUTOMATIC_ORDER_SUBMISSION_REJECTED")

        return {
            "request_id": request["request_id"],
            "policy_pass": not blockers,
            "blockers": blockers,
            "preview_allowed": not blockers,
            "actual_change_allowed": False,
            "actual_change_applied": False,
        }


class KillSwitchState:
    def preview(self, requested_state: str) -> dict[str, Any]:
        if requested_state not in {
            "ACTIVATE_PREVIEW",
            "DEACTIVATE_PREVIEW",
        }:
            raise ValueError("INVALID_KILL_SWITCH_STATE")
        return {
            "requested_state": requested_state,
            "current_actual_state": "UNCHANGED",
            "preview_state": requested_state,
            "actual_kill_switch_changed": False,
            "broker_cancel_attempted": False,
            "runtime_stop_attempted": False,
            "network_used": False,
        }
