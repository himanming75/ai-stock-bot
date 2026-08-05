from __future__ import annotations
import json
from pathlib import Path
from typing import Any


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        return {
            "_read_error": str(exc),
            "_path": str(path),
        }


def tail_jsonl(path: Path, limit: int = 20) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    lines = path.read_text(
        encoding="utf-8-sig",
        errors="replace",
    ).splitlines()[-limit:]
    result = []
    for line in lines:
        try:
            result.append(json.loads(line))
        except Exception:
            result.append({"raw": line})
    return result


def collect_status(root: Path) -> dict[str, Any]:
    p1 = root / "release/p1_broker_consolidation/actual"
    p2 = root / "release/p2_actual_paper_execution/actual"
    p3 = root / "release/p3_order_fill_portfolio_sync/actual"
    p4 = root / "release/p4_autonomous_paper_runtime/actual"
    p5 = root / "release/p5_paper_long_run_qualification/actual"
    ops = root / "release/operations_bundle/actual"

    kill_switch = read_json(
        p1 / "kill_switch.json",
        {"kill_switch_active": True, "reason": "MISSING"},
    )
    actual_validation = {
        "p2": read_json(
            p2 / "p2_actual_validation.json",
            {"validated": False},
        ),
        "p3": read_json(
            p3 / "p3_actual_validation.json",
            {"validated": False},
        ),
        "p4": read_json(
            p4 / "p4_actual_validation.json",
            {"validated": False},
        ),
    }

    heartbeat = read_json(p4 / "heartbeat.json", {})
    p4_result = read_json(p4 / "p4_runtime_result.json", {})
    p5_result = read_json(p5 / "p5_qualification_result.json", {})
    p2_result = read_json(
        p1 / "latest_p2_execution_result.json",
        {},
    )
    p3_result = read_json(
        p3 / "actual_p3_sync_result.json",
        read_json(p3 / "p3_sync_result.json", {}),
    )

    return {
        "mode": {
            "paper": True,
            "live": False,
            "live_activation_allowed": False,
        },
        "kill_switch": kill_switch,
        "actual_validation": actual_validation,
        "runtime": {
            "heartbeat": heartbeat,
            "p4_result": p4_result,
        },
        "execution": {
            "latest_p2": p2_result,
            "latest_p3": p3_result,
        },
        "qualification": {
            "p5": p5_result,
            "paper_complete": False,
            "live_complete": False,
        },
        "recent_events": tail_jsonl(
            ops / "operations_events.jsonl",
            30,
        ),
        "recent_order_events": tail_jsonl(
            p1 / "order_ledger.jsonl",
            20,
        ),
        "recent_fill_events": tail_jsonl(
            p3 / "actual_fill_ledger.jsonl",
            20,
        ),
        "recent_drift_events": tail_jsonl(
            p3 / "actual_drift_ledger.jsonl",
            20,
        ),
    }
