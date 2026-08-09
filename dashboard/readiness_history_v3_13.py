
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json

HISTORY_REL = Path("runtime/dashboard_strategy_readiness_v3_13/readiness_history.jsonl")
MILESTONES = (10, 20, 50, 100)

def _history_path(root: Path) -> Path:
    return root / HISTORY_REL

def _read_history(root: Path, max_rows: int = 500):
    path = _history_path(root)
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()[-max_rows:]
    except Exception:
        return []
    rows = []
    for line in lines:
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except Exception:
            continue
        if isinstance(value, dict):
            rows.append(value)
    return rows

def _fingerprint(readiness: dict, utc_date: str) -> str:
    payload = {
        "date": utc_date,
        "status": readiness.get("status"),
        "trade_count": readiness.get("canonical_numeric_trade_count"),
        "overall_score": readiness.get("overall_score"),
        "scores": readiness.get("scores") or {},
        "blockers": readiness.get("blockers") or [],
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def _snapshot(readiness: dict, now_utc: datetime) -> dict:
    scores = readiness.get("scores") or {}
    return {
        "recorded_at_utc": now_utc.isoformat(),
        "utc_date": now_utc.date().isoformat(),
        "status": readiness.get("status"),
        "overall_score": readiness.get("overall_score"),
        "raw_overall_score": readiness.get("raw_overall_score"),
        "canonical_numeric_trade_count": int(readiness.get("canonical_numeric_trade_count") or 0),
        "scores": {
            "sample_confidence": scores.get("sample_confidence"),
            "profitability_quality": scores.get("profitability_quality"),
            "risk_quality": scores.get("risk_quality"),
            "consistency": scores.get("consistency"),
            "diversification": scores.get("diversification"),
        },
        "blockers": list(readiness.get("blockers") or []),
    }

def record_if_changed(root: Path, readiness: dict, now_utc: datetime | None = None):
    now_utc = now_utc or datetime.now(timezone.utc)
    snap = _snapshot(readiness, now_utc)
    snap["fingerprint"] = _fingerprint(readiness, snap["utc_date"])

    history = _read_history(root)
    latest = history[-1] if history else None

    if latest and latest.get("fingerprint") == snap["fingerprint"]:
        return {
            "written": False,
            "reason": "UNCHANGED_FINGERPRINT",
            "snapshot": latest,
        }

    path = _history_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(snap, sort_keys=True) + "\n")

    return {
        "written": True,
        "reason": "NEW_EVIDENCE_STATE",
        "snapshot": snap,
    }

def _milestone_state(history: list[dict]):
    reached = []
    first_reached = {}
    for milestone in MILESTONES:
        for row in history:
            count = int(row.get("canonical_numeric_trade_count") or 0)
            if count >= milestone:
                reached.append(milestone)
                first_reached[str(milestone)] = {
                    "recorded_at_utc": row.get("recorded_at_utc"),
                    "canonical_numeric_trade_count": count,
                    "overall_score": row.get("overall_score"),
                    "status": row.get("status"),
                }
                break

    max_count = max(
        [int(r.get("canonical_numeric_trade_count") or 0) for r in history] or [0]
    )
    next_milestone = next((m for m in MILESTONES if m > max_count), None)

    return {
        "reached": reached,
        "first_reached": first_reached,
        "next_milestone": next_milestone,
        "current_max_trade_count": max_count,
    }

def build_history_summary(root: Path, current_readiness: dict):
    write_result = record_if_changed(root, current_readiness)
    history = _read_history(root)

    status_changes = []
    previous_status = None
    for row in history:
        status = row.get("status")
        if previous_status is not None and status != previous_status:
            status_changes.append({
                "recorded_at_utc": row.get("recorded_at_utc"),
                "from_status": previous_status,
                "to_status": status,
                "overall_score": row.get("overall_score"),
                "canonical_numeric_trade_count": row.get("canonical_numeric_trade_count"),
            })
        previous_status = status

    latest = history[-1] if history else None
    previous = history[-2] if len(history) >= 2 else None

    score_delta = None
    trade_count_delta = None
    if latest and previous:
        try:
            score_delta = round(
                float(latest.get("overall_score") or 0)
                - float(previous.get("overall_score") or 0),
                2,
            )
        except Exception:
            score_delta = None
        trade_count_delta = (
            int(latest.get("canonical_numeric_trade_count") or 0)
            - int(previous.get("canonical_numeric_trade_count") or 0)
        )

    trend = [
        {
            "recorded_at_utc": row.get("recorded_at_utc"),
            "utc_date": row.get("utc_date"),
            "status": row.get("status"),
            "overall_score": row.get("overall_score"),
            "canonical_numeric_trade_count": row.get("canonical_numeric_trade_count"),
            "scores": row.get("scores") or {},
        }
        for row in history[-120:]
    ]

    return {
        "stage": "V3.13_READINESS_HISTORY_EVIDENCE_TREND",
        "status": "PASS",
        "history_file": str(HISTORY_REL).replace("\\", "/"),
        "history_record_count": len(history),
        "write_result": {
            "written": write_result["written"],
            "reason": write_result["reason"],
        },
        "latest": latest,
        "previous": previous,
        "score_delta_from_previous": score_delta,
        "trade_count_delta_from_previous": trade_count_delta,
        "milestones": _milestone_state(history),
        "status_changes": status_changes[-50:],
        "trend": trend,
        "contracts": {
            "analytics_history_write_only": True,
            "paper_runtime_modified": False,
            "broker_network_used": False,
            "broker_write_performed": False,
            "order_submission_performed": False,
            "production_parameter_modified": False,
            "production_selector_modified": False,
            "automatic_promotion": False,
            "live_approval": False,
            "duplicate_engine_created": False,
        },
    }
