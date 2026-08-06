from __future__ import annotations
import json
from pathlib import Path
from typing import Any


EMPTY_PORTAL = {
    "run_id": None,
    "generated_at": None,
    "mode": "READ_ONLY",
    "overall_status": "NO_DATA",
    "broker_cards": [],
    "totals": {
        "brokers": 0,
        "accounts": 0,
        "positions": 0,
        "orders": 0,
        "reconciliation_issues": 0,
        "errors": 0,
    },
    "issues": [],
    "errors": [],
    "broker_write_enabled": False,
    "order_submission_enabled": False,
    "order_cancel_enabled": False,
}


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        value = json.loads(
            path.read_text(encoding="utf-8")
        )
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def load_portal_snapshot(path: Path) -> dict[str, Any]:
    value = load_json(path)
    result = dict(EMPTY_PORTAL)
    result.update(value)
    totals = dict(EMPTY_PORTAL["totals"])
    totals.update(
        value.get("totals", {})
        if isinstance(value.get("totals"), dict)
        else {}
    )
    result["totals"] = totals
    result["broker_cards"] = (
        value.get("broker_cards", [])
        if isinstance(value.get("broker_cards"), list)
        else []
    )
    result["issues"] = (
        value.get("issues", [])
        if isinstance(value.get("issues"), list)
        else []
    )
    result["errors"] = (
        value.get("errors", [])
        if isinstance(value.get("errors"), list)
        else []
    )
    result["broker_write_enabled"] = False
    result["order_submission_enabled"] = False
    result["order_cancel_enabled"] = False
    return result


def load_sync_result(path: Path) -> dict[str, Any]:
    value = load_json(path)
    snapshots = value.get("snapshots", {})
    if not isinstance(snapshots, dict):
        snapshots = {}
    return {
        "status": value.get("status", "NO_DATA"),
        "partial_success": bool(
            value.get("partial_success", False)
        ),
        "sources": (
            value.get("sources", [])
            if isinstance(value.get("sources"), list)
            else []
        ),
        "snapshots": snapshots,
        "issues": (
            value.get("issues", [])
            if isinstance(value.get("issues"), list)
            else []
        ),
        "errors": (
            value.get("errors", [])
            if isinstance(value.get("errors"), list)
            else []
        ),
    }


def build_detail(sync_result: dict) -> dict:
    snapshots = sync_result.get("snapshots", {})
    accounts = []
    positions = []
    orders = []
    quotes = []

    for broker, snapshot in sorted(
        snapshots.items()
    ):
        if not isinstance(snapshot, dict):
            continue
        for name, target in (
            ("accounts", accounts),
            ("positions", positions),
            ("orders", orders),
            ("quotes", quotes),
        ):
            items = snapshot.get(name, [])
            if not isinstance(items, list):
                continue
            for item in items:
                if isinstance(item, dict):
                    row = dict(item)
                    row.setdefault("broker", broker)
                    target.append(row)

    return {
        "accounts": accounts,
        "positions": positions,
        "orders": orders,
        "quotes": quotes,
        "sources": sync_result.get("sources", []),
        "issues": sync_result.get("issues", []),
        "errors": sync_result.get("errors", []),
        "partial_success": sync_result.get(
            "partial_success",
            False,
        ),
    }
