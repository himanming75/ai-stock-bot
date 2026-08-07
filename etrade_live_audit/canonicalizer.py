from __future__ import annotations

import json
from pathlib import Path
from typing import Any


CAPABILITIES = {
    "oauth_authentication": (
        "OAuth 1.0a authentication",
        [
            "multi_broker_etrade/auth.py",
            "broker_plugin_packages/etrade/plugin.py",
            "multi_broker_etrade/client.py",
        ],
        ("oauth", "token", "consumer", "auth"),
    ),
    "production_endpoint": (
        "Production endpoint configuration",
        [
            "multi_broker_etrade/client.py",
            "broker_plugin_packages/etrade/plugin.py",
            "multi_broker_etrade/config.py",
        ],
        ("api.etrade.com", "production", "base_url", "etrade"),
    ),
    "credential_separation": (
        "Live credential separation",
        [
            "deployment/credential_vault.py",
            "multi_broker_etrade/config.py",
            "broker_plugin_packages/etrade/plugin.py",
        ],
        ("credential", "consumer_key", "consumer_secret", "production"),
    ),
    "accounts_read": (
        "Account and balance read",
        [
            "multi_broker_etrade/accounts.py",
            "broker_plugin_packages/etrade/plugin.py",
            "multi_broker_etrade/client.py",
        ],
        ("account", "balance", "list_accounts"),
    ),
    "positions_read": (
        "Position read",
        [
            "multi_broker_etrade/accounts.py",
            "broker_plugin_packages/etrade/plugin.py",
            "multi_broker_etrade/client.py",
        ],
        ("position", "portfolio"),
    ),
    "market_data_read": (
        "Quote and market data read",
        [
            "multi_broker_etrade/market.py",
            "broker_plugin_packages/etrade/plugin.py",
            "multi_broker_etrade/client.py",
        ],
        ("quote", "market", "symbol"),
    ),
    "order_preview": (
        "Order preview",
        [
            "multi_broker_etrade/orders.py",
            "broker_plugin_packages/etrade/plugin.py",
            "multi_broker_etrade/client.py",
        ],
        ("preview", "order"),
    ),
    "order_place": (
        "Order placement",
        [
            "multi_broker_etrade/orders.py",
            "broker_plugin_packages/etrade/plugin.py",
            "multi_broker_etrade/client.py",
        ],
        ("place", "submit", "order"),
    ),
    "order_status": (
        "Order status read",
        [
            "multi_broker_etrade/orders.py",
            "broker_plugin_packages/etrade/plugin.py",
            "multi_broker_etrade/client.py",
        ],
        ("status", "list_orders", "order"),
    ),
    "order_cancel": (
        "Order cancellation",
        [
            "multi_broker_etrade/orders.py",
            "broker_plugin_packages/etrade/plugin.py",
            "multi_broker_etrade/client.py",
        ],
        ("cancel", "order"),
    ),
    "duplicate_prevention": (
        "Duplicate order prevention",
        [
            "broker_safe_execution/gateway.py",
            "multi_broker_etrade/safety.py",
            "broker_integration/execution_service.py",
        ],
        ("duplicate", "idempot", "client_order", "request_id"),
    ),
    "risk_limits": (
        "Live order risk limits",
        [
            "broker_safe_execution/gateway.py",
            "risk_manager/service.py",
            "actual_market_validation/service.py",
        ],
        ("max_order", "daily_loss", "risk", "limit"),
    ),
    "kill_switch": (
        "Live kill switch",
        [
            "broker_safe_execution/gateway.py",
            "operations_manager/recovery.py",
            "multi_broker_etrade/safety.py",
        ],
        ("kill", "halt", "emergency", "disable"),
    ),
    "restart_reconciliation": (
        "Restart and live reconciliation",
        [
            "broker_integration/actual_validation.py",
            "operations_manager/recovery.py",
            "broker_sync/service.py",
        ],
        ("reconcil", "restart", "recover"),
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
    "etrade": 20,
    "service": 12,
    "client": 10,
    "plugin": 8,
    "gateway": 10,
    "safety": 10,
    "production": 8,
    "live": 7,
    "reconciliation": 8,
    "recovery": 8,
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
    if "sandbox" in low or "mock" in low or "offline" in low:
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
    normalized_path = _normalize(item["path"])
    if normalized_path in preferred:
        return True

    patterns = CAPABILITIES[capability][2]
    if capability in {
        "oauth_authentication",
        "production_endpoint",
        "accounts_read",
        "positions_read",
        "market_data_read",
        "order_preview",
        "order_place",
        "order_status",
        "order_cancel",
    }:
        if "etrade" not in text:
            return False

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


def canonicalize_etrade_live(audit: dict[str, Any]) -> dict[str, Any]:
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
                candidate["etrade_live_score"] = _score(capability, item)
                candidates.append(candidate)

        candidates.sort(
            key=lambda item: (
                item["etrade_live_score"],
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

    live_write_paths = []
    for capability in ("order_place", "order_cancel"):
        item = selected[capability]["selected"]
        if item:
            live_write_paths.append(item["path"])

    return {
        "stage": "PHASE3_ETRADE_LIVE_CANONICALIZATION",
        "status": "PASS" if not missing else "REVIEW_REQUIRED",
        "scope_locked": True,
        "broker_scope": {
            "paper_broker": "ALPACA",
            "live_broker": "ETRADE",
            "other_brokers_enabled": False,
        },
        "etrade_live_submission_enabled": False,
        "etrade_live_cancel_enabled": False,
        "etrade_live_allocation_enabled": False,
        "actual_market_day_validation_performed": False,
        "actual_live_orders_submitted": 0,
        "actual_live_orders_cancelled": 0,
        "selected": selected,
        "missing_capabilities": missing,
        "live_write_paths": live_write_paths,
        "deferred_until_after_operation": [
            "ETRADE_OPTIONS",
            "ETRADE_MARGIN",
            "ETRADE_SHORT_SELLING",
            "MULTIPLE_ETRADE_ACCOUNTS",
            "OTHER_BROKERS",
            "SMART_ORDER_ROUTING",
        ],
    }


def save_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
