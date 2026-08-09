
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import argparse, json, sys

def age_minutes(path: Path):
    if not path.exists():
        return None
    return round(
        max(0, datetime.now(timezone.utc).timestamp() - path.stat().st_mtime) / 60,
        2,
    )

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", default=r"C:\stock-bot")
    p.add_argument("--write", action="store_true")
    a = p.parse_args()
    root = Path(a.root)

    sys.path.insert(0, str(root))
    from dashboard.operations_dashboard_v3_2 import build_status

    s = build_status(root)
    alerts = []

    if str(s.get("health", {}).get("overall", "")).startswith("BLOCKED"):
        alerts.append({
            "severity": "CRITICAL",
            "code": "SYSTEM_BLOCKED",
            "message": s["health"]["overall"],
        })

    gate = s.get("runtime_gate", {})
    if int(gate.get("successful_hooks", 0) or 0) < int(gate.get("required_hooks", 3) or 3):
        alerts.append({
            "severity": "INFO",
            "code": "RUNTIME_GATE_WAITING",
            "message": f"Hooks {gate.get('successful_hooks',0)}/{gate.get('required_hooks',3)}",
        })

    tw = s.get("two_week", {})
    if int(tw.get("completed_days", 0) or 0) < int(tw.get("required_days", 10) or 10):
        alerts.append({
            "severity": "INFO",
            "code": "TWO_WEEK_PROGRESS",
            "message": f"Validation {tw.get('completed_days',0)}/{tw.get('required_days',10)}",
        })

    git = s.get("git", {})
    if git.get("available") is False:
        alerts.append({
            "severity": "WARNING",
            "code": "GIT_UNAVAILABLE",
            "message": git.get("error") or "Git unavailable",
        })
    elif git.get("synced") is False:
        alerts.append({
            "severity": "WARNING",
            "code": "GIT_NOT_SYNCED",
            "message": "Local HEAD differs from origin/main",
        })

    watched = {
        "paper_session": root / "runtime/paper_autonomous_daily_session/session_ledger.jsonl",
        "runtime_gate": root / "runtime/regime_aware_buy_shadow_v2_9_4/latest_runtime_observation_gate_v2_9_4.json",
        "two_week": root / "runtime/paper_2week_validation_v3_0/latest_validation_report.json",
    }

    freshness = {
        name: {"exists": path.exists(), "age_minutes": age_minutes(path)}
        for name, path in watched.items()
    }

    for name, meta in freshness.items():
        if not meta["exists"]:
            alerts.append({
                "severity": "WARNING",
                "code": f"{name.upper()}_MISSING",
                "message": f"{name} source missing",
            })

    summary = {
        "critical": sum(1 for x in alerts if x["severity"] == "CRITICAL"),
        "warning": sum(1 for x in alerts if x["severity"] == "WARNING"),
        "info": sum(1 for x in alerts if x["severity"] == "INFO"),
        "total": len(alerts),
    }

    result = {
        "stage": "V3.3_DASHBOARD_HEALTH_SNAPSHOT",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "summary": summary,
        "alerts": alerts,
        "freshness": freshness,
        "contracts": {
            "broker_write": False,
            "order_submission": False,
            "production_modified": False,
        },
    }

    if a.write:
        out = root / "runtime/dashboard_health_v3_3/latest_health_snapshot.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print(json.dumps(result, indent=2))
    return 2 if summary["critical"] else 0

if __name__ == "__main__":
    raise SystemExit(main())
