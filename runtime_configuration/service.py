from __future__ import annotations
import json
from pathlib import Path
from typing import Any

from configuration_profiles.loader import load_profile

from .binding import (
    bind_profile_to_runtime,
    build_order_router_binding,
    build_risk_binding,
    build_strategy_binding,
)
from .gates import evaluate_runtime_bridge_gate


def build_runtime_bridge_preview(
    root: Path,
    profile_path: Path,
) -> dict[str, Any]:
    profile, validation = load_profile(profile_path)
    if not validation["valid"]:
        return {
            "stage": "R5_RUNTIME_BRIDGE_PREVIEW",
            "status": "FAIL",
            "profile_name": profile.profile_name,
            "validation": validation,
            "failed": validation["failed"],
            "actual_runtime_activation_performed": False,
            "actual_paper_orders_submitted": 0,
            "actual_live_orders_submitted": 0,
        }

    runtime = bind_profile_to_runtime(profile)
    gate = evaluate_runtime_bridge_gate(
        root,
        broker_mode=runtime.broker_mode,
    )

    preview_allowed = (
        gate["preview_allowed"]
        and runtime.profile_enabled
    )

    return {
        "stage": "R5_RUNTIME_BRIDGE_PREVIEW",
        "status": "PASS",
        "profile_name": runtime.profile_name,
        "broker_mode": runtime.broker_mode,
        "horizon": runtime.horizon,
        "profile_enabled": runtime.profile_enabled,
        "runtime_configuration": runtime.as_json(),
        "strategy_binding": build_strategy_binding(runtime),
        "risk_binding": build_risk_binding(runtime),
        "order_router_binding": build_order_router_binding(runtime),
        "gate": gate,
        "preview_allowed": preview_allowed,
        "actual_runtime_activation_performed": False,
        "broker_network_used": False,
        "broker_write_enabled": False,
        "automatic_order_submission_enabled": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
    }


def write_runtime_bridge_preview(
    root: Path,
    profile_path: Path,
) -> dict[str, Any]:
    result = build_runtime_bridge_preview(root, profile_path)
    actual = (
        root / "release/r5_runtime_configuration_bridge/actual"
    )
    actual.mkdir(parents=True, exist_ok=True)
    (actual / "last_runtime_bridge_preview.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result
