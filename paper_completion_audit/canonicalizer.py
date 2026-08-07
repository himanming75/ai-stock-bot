from __future__ import annotations

import json
from pathlib import Path
from typing import Any


EXCLUDED_PATH_PARTS = {
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "node_modules",
    "dist",
    "build",
    "runtime",
    "output",
    "logs",
    "tmp",
    "temp",
    "bundle",
    "bundles",
    "archive",
    "archives",
    "fixtures",
    "fixture",
    "samples",
    "sample",
    "examples",
    "example",
    "tests",
    "test",
    "backtest",
    "sandbox",
    "mock",
    "mocks",
}

EXCLUDED_PREFIXES = (
    "test_",
    "tools/test_",
    "release/",
)

EXCLUDED_NAME_TOKENS = {
    "offline",
    "sample",
    "example",
    "fixture",
    "mock",
    "sandbox",
    "deprecated",
    "legacy",
    "backup",
    "old",
}

PREFERRED_NAME_TOKENS = {
    "actual": 12,
    "controller": 12,
    "service": 10,
    "engine": 9,
    "runtime": 9,
    "manager": 8,
    "operations": 8,
    "reconciliation": 10,
    "validation": 8,
    "certification": 8,
    "gateway": 6,
    "adapter": 5,
    "watchdog": 10,
    "recovery": 10,
    "checkpoint": 8,
    "lock": 8,
    "end_of_day": 10,
    "dashboard": 6,
}

CATEGORY_PRIORITY = {
    "credentials_profiles": [
        "deployment/credential_gate.py",
        "deployment/credential_vault.py",
        "deployment/configuration_profiles.py",
    ],
    "market_polling": [
        "actual_market_polling/service.py",
        "actual_market_polling/collector.py",
        "alpaca_market_data/actual_market_polling.py",
    ],
    "signals_strategy": [
        "multi_timeframe_ai/service.py",
        "ai_strategy/engine.py",
        "strategy_engine/service.py",
    ],
    "risk_approval": [
        "risk_manager/service.py",
        "risk_manager/engine.py",
        "broker_safe_execution/gateway.py",
    ],
    "order_submission": [
        "alpaca_paper_operations/engine.py",
        "paper_submission_gate/service.py",
        "controlled_paper_execution/engine.py",
        "real_paper_micro_order/engine.py",
    ],
    "order_lifecycle": [
        "order_lifecycle/service.py",
        "broker_integration/actual_validation.py",
        "alpaca_market_data/position_account_reconciliation_v86_41_60.py",
    ],
    "positions_portfolio": [
        "portfolio/position_manager.py",
        "portfolio_manager/service.py",
        "realtime_portfolio_monitoring/service.py",
    ],
    "session_orchestration": [
        "paper_automation_controller/controller.py",
        "daily_session_manager/service.py",
        "autonomous_paper_runtime/limited_autonomous_paper_trading.py",
    ],
    "restart_recovery": [
        "operations_manager/recovery.py",
        "automation_watchdog/recovery.py",
        "paper_automation_controller/checkpoint.py",
    ],
    "end_of_day": [
        "paper_runtime/end_of_day_v82_33_36.py",
        "end_of_day_manager/service.py",
    ],
    "monitoring_dashboard": [
        "web_controller/operations_api.py",
        "operations_manager/notifications.py",
        "system_health_monitoring/service.py",
    ],
    "paper_completion": [
        "actual_validation/paper_completion.py",
        "paper_completion/service.py",
        "p5_long_run_qualification/service.py",
    ],
}


def _normalize(path: str) -> str:
    return path.replace("\\", "/").strip("/")


def _excluded(path: str) -> bool:
    normalized = _normalize(path)
    low = normalized.lower()
    parts = set(low.split("/"))
    if any(part in EXCLUDED_PATH_PARTS for part in parts):
        return True
    if any(low.startswith(prefix) for prefix in EXCLUDED_PREFIXES):
        return True
    name = Path(low).name
    if name.startswith("test_"):
        return True
    stem_tokens = set(Path(low).stem.replace("-", "_").split("_"))
    if stem_tokens & EXCLUDED_NAME_TOKENS:
        return True
    return False


def _priority_score(category: str, path: str) -> int:
    normalized = _normalize(path)
    low = normalized.lower()

    exact_list = CATEGORY_PRIORITY.get(category, [])
    if normalized in exact_list:
        return 10000 - exact_list.index(normalized)

    score = 0
    for token, value in PREFERRED_NAME_TOKENS.items():
        if token in low:
            score += value

    depth = len(Path(normalized).parts)
    score -= depth

    if low.endswith("/__init__.py"):
        score -= 30
    if "/tools/" in f"/{low}/":
        score -= 20
    if low.endswith(".ps1"):
        score -= 12
    if low.endswith(".json"):
        score -= 25
    if low.endswith(".md") or low.endswith(".txt"):
        score -= 40

    return score


def _safe_runtime_candidate(item: dict[str, Any]) -> bool:
    path = _normalize(item["path"])
    if _excluded(path):
        return False

    suffix = Path(path).suffix.lower()
    if suffix != ".py":
        return False

    flags = item.get("safety_flags", {})
    if flags.get("contains_delete_all_positions"):
        return False

    return True


def canonicalize(audit: dict[str, Any]) -> dict[str, Any]:
    category_candidates: dict[str, list[dict[str, Any]]] = {
        category: [] for category in CATEGORY_PRIORITY
    }

    for item in audit.get("records", []):
        if not _safe_runtime_candidate(item):
            continue
        for category in item.get("categories", []):
            if category not in category_candidates:
                continue
            candidate = dict(item)
            candidate["canonical_score"] = (
                _priority_score(category, item["path"])
                + int(item.get("score", 0))
            )
            category_candidates[category].append(candidate)

    selected = {}
    missing = []
    for category, candidates in category_candidates.items():
        candidates.sort(
            key=lambda item: (
                item["canonical_score"],
                item.get("modified_ns", 0),
                -len(item["path"]),
            ),
            reverse=True,
        )
        if candidates:
            selected[category] = {
                "selected": candidates[0],
                "alternatives": candidates[1:5],
                "candidate_count": len(candidates),
            }
        else:
            selected[category] = {
                "selected": None,
                "alternatives": [],
                "candidate_count": 0,
            }
            missing.append(category)

    selected_write_paths = []
    for category in ("order_submission", "order_lifecycle"):
        chosen = selected[category]["selected"]
        if chosen:
            selected_write_paths.append(chosen["path"])

    unsafe_selected = []
    for category, result in selected.items():
        item = result["selected"]
        if not item:
            continue
        flags = item.get("safety_flags", {})
        if (
            category == "order_submission"
            and flags.get("contains_submit_order")
            and not (
                flags.get("mentions_paper_only")
                or flags.get("mentions_live_off")
                or flags.get("mentions_broker_write_off")
            )
        ):
            unsafe_selected.append(item["path"])

    return {
        "stage": "PAPER_TRADING_1_0_CANONICALIZER",
        "scope_locked": True,
        "new_feature_development_allowed": False,
        "actual_market_day_validation_performed": False,
        "selected": selected,
        "missing_categories": missing,
        "selected_write_paths": selected_write_paths,
        "unsafe_selected_paths": unsafe_selected,
        "status": (
            "PASS"
            if not missing and not unsafe_selected
            else "REVIEW_REQUIRED"
        ),
    }


def save_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
