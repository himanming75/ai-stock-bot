import json
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    path = root / "release/v85_01_to_v85_08/actual/dashboard_v2_state.json"
    if not path.exists():
        print(f"STATE NOT FOUND: {path}")
        return 1
    state = json.loads(path.read_text(encoding="utf-8"))
    checks = {
        "stage_range": state.get("dashboard_stage_range") == "V85.01-V85.08",
        "safe_state": state.get("dashboard_state") in {
            "DASHBOARD_V2_SAFE",
            "DASHBOARD_V2_ATTENTION_REQUIRED",
        },
        "read_only": state.get("read_only") is True,
        "paper_only": state.get("paper_only") is True,
        "broker_write_disabled": state.get("broker_write_enabled") is False,
        "order_submission_disabled": (
            state.get("order_submission_enabled") is False
        ),
        "live_trading_disabled": state.get("live_trading_enabled") is False,
        "external_network_disabled": (
            state.get("external_network_enabled") is False
        ),
        "source_count": state.get("total_source_count") == 4,
    }
    failed = [name for name, passed in checks.items() if not passed]
    payload = {
        "verification_stage": "V85.08",
        "verification_status": "PASS" if not failed else "FAIL",
        "dashboard_state": state.get("dashboard_state"),
        "checks": checks,
        "failed": failed,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
