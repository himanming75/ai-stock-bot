from __future__ import annotations

import json
from pathlib import Path
from typing import Any


CAPABILITIES = {
    "alpaca_paper_account_binding": (
        "Alpaca Paper account binding",
        [
            "deployment/credential_vault.py",
            "alpaca_paper_operations/engine.py",
            "broker_integration/actual_validation.py",
        ],
        ("alpaca", "paper", "account"),
    ),
    "etrade_live_account_binding": (
        "E*TRADE Live account binding",
        [
            "deployment/credential_vault.py",
            "broker_plugin_packages/etrade/plugin.py",
            "broker_integration/actual_validation.py",
        ],
        ("etrade", "account", "live"),
    ),
    "account_id_allowlist": (
        "Allowed account ID enforcement",
        [
            "deployment/configuration_profiles.py",
            "deployment/credential_vault.py",
            "broker_safe_execution/gateway.py",
        ],
        ("account_id", "allow", "profile"),
    ),
    "broker_account_role_lock": (
        "Broker and account role lock",
        [
            "broker_safe_execution/gateway.py",
            "actual_market_validation/service.py",
            "broker_integration/execution_service.py",
        ],
        ("broker", "account", "paper", "live"),
    ),
    "pre_order_account_validation": (
        "Pre-order account validation",
        [
            "broker_safe_execution/gateway.py",
            "actual_market_validation/service.py",
            "broker_integration/actual_validation.py",
        ],
        ("validate", "account", "order"),
    ),
    "credential_account_match": (
        "Credential and account match",
        [
            "deployment/credential_vault.py",
            "broker_integration/actual_validation.py",
            "actual_market_validation/service.py",
        ],
        ("credential", "account", "match"),
    ),
    "restart_account_revalidation": (
        "Restart account revalidation",
        [
            "operations_manager/recovery.py",
            "broker_integration/actual_validation.py",
            "paper_automation_controller/checkpoint.py",
        ],
        ("restart", "recover", "account", "reconcil"),
    ),
    "checkpoint_account_identity": (
        "Checkpoint account identity",
        [
            "paper_automation_controller/checkpoint.py",
            "operations_manager/recovery.py",
            "autonomous_paper_runtime/limited_autonomous_paper_trading.py",
        ],
        ("checkpoint", "account", "identity"),
    ),
    "dashboard_account_visibility": (
        "Broker, account and mode visibility",
        [
            "system_health_monitoring/service.py",
            "web_controller/operations_api.py",
            "realtime_portfolio_monitoring/service.py",
        ],
        ("dashboard", "account", "broker", "mode"),
    ),
    "wrong_account_hard_block": (
        "Wrong account hard block",
        [
            "broker_safe_execution/gateway.py",
            "actual_market_validation/service.py",
            "broker_integration/actual_validation.py",
        ],
        ("block", "account", "mismatch"),
    ),
    "single_account_runtime_lock": (
        "Single-account runtime lock",
        [
            "paper_automation_controller/controller.py",
            "operations_manager/recovery.py",
            "autonomous_paper_runtime/limited_autonomous_paper_trading.py",
        ],
        ("lock", "single", "account", "runtime"),
    ),
    "account_switch_prohibition": (
        "Runtime account switch prohibition",
        [
            "broker_safe_execution/gateway.py",
            "operations_manager/recovery.py",
            "deployment/configuration_profiles.py",
        ],
        ("switch", "account", "prohibit", "lock"),
    ),
}

EXCLUDED_PARTS = {
    ".git", ".venv", "__pycache__", ".pytest_cache", "node_modules",
    "release", "runtime", "output", "dist", "build", "tests", "test",
    "fixtures", "fixture", "samples", "sample", "examples", "example",
    "mock", "mocks", "sandbox", "backtest",
}

EXCLUDED_TOKENS = {
    "test", "mock", "sample", "fixture", "example", "deprecated",
    "legacy", "backup", "old", "offline", "sandbox",
}

POSITIVE_TOKENS = {
    "account": 12,
    "binding": 12,
    "credential": 10,
    "vault": 10,
    "gateway": 10,
    "validation": 10,
    "recovery": 8,
    "checkpoint": 8,
    "controller": 7,
    "monitoring": 6,
    "service": 6,
}


def _normalize(value: str) -> str:
    return value.replace("\\", "/").strip("/")


def _is_operational_python(path: str) -> bool:
    normalized = _normalize(path)
    low = normalized.lower()
    parts = low.split("/")
    if Path(low).suffix != ".py":
        return False
    if any(part in EXCLUDED_PARTS for part in parts):
        return False
    name_tokens = set(Path(low).stem.replace("-", "_").split("_"))
    if name_tokens & EXCLUDED_TOKENS:
        return False
    if Path(low).name.startswith("test_"):
        return False
    if low.startswith("tools/test_"):
        return False
    return True


def _matches(capability: str, item: dict[str, Any]) -> bool:
    path = _normalize(item["path"]).lower()
    functions = " ".join(item.get("functions", [])).lower()
    classes = " ".join(item.get("classes", [])).lower()
    text = f"{path} {functions} {classes}"

    preferred = CAPABILITIES[capability][1]
    if _normalize(item["path"]) in preferred:
        return True

    patterns = CAPABILITIES[capability][2]
    return any(pattern in text for pattern in patterns)


def _score(capability: str, item: dict[str, Any]) -> int:
    path = _normalize(item["path"])
    low = path.lower()
    preferred = CAPABILITIES[capability][1]
    if path in preferred:
        return 10000 - preferred.index(path)

    score = int(item.get("score", 0))
    for token, bonus in POSITIVE_TOKENS.items():
        if token in low:
            score += bonus
    score -= len(Path(path).parts)
    if low.startswith("tools/"):
        score -= 20
    if low.endswith("/__init__.py"):
        score -= 30
    return score


def canonicalize_single_account(audit: dict[str, Any]) -> dict[str, Any]:
    records = [
        item for item in audit.get("records", [])
        if _is_operational_python(item["path"])
    ]

    selected = {}
    missing = []

    for capability, (label, _, _) in CAPABILITIES.items():
        candidates = []
        for item in records:
            if _matches(capability, item):
                candidate = dict(item)
                candidate["single_account_score"] = _score(
                    capability, item
                )
                candidates.append(candidate)

        candidates.sort(
            key=lambda item: (
                item["single_account_score"],
                item.get("modified_ns", 0),
                -len(item["path"]),
            ),
            reverse=True,
        )

        selected[capability] = {
            "label": label,
            "selected": candidates[0] if candidates else None,
            "alternatives": candidates[1:5],
            "candidate_count": len(candidates),
        }
        if not candidates:
            missing.append(capability)

    return {
        "stage": "PHASE4_SINGLE_ACCOUNT_BINDING_CANONICALIZATION",
        "status": "PASS" if not missing else "REVIEW_REQUIRED",
        "scope_locked": True,
        "multi_account_enabled": False,
        "account_roles": {
            "alpaca": {
                "mode": "PAPER_ONLY",
                "allowed_account_count": 1,
            },
            "etrade": {
                "mode": "LIVE_ONLY",
                "allowed_account_count": 1,
            },
        },
        "runtime_account_switch_enabled": False,
        "automatic_account_discovery_enabled": False,
        "live_submission_enabled": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
        "selected": selected,
        "missing_capabilities": missing,
        "deferred_until_after_operation": [
            "MULTIPLE_ALPACA_ACCOUNTS",
            "MULTIPLE_ETRADE_ACCOUNTS",
            "FAMILY_ACCOUNT_MANAGEMENT",
            "CORPORATE_ACCOUNT_MANAGEMENT",
            "ACCOUNT_LEVEL_STRATEGY_ROUTING",
            "CROSS_ACCOUNT_REBALANCING",
        ],
    }


def save_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
