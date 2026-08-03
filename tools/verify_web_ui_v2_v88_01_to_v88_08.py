import json
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    path = root / "release/v88_01_to_v88_08/actual/web_ui_v2_state.json"
    if not path.exists():
        print(f"STATE NOT FOUND: {path}")
        return 1

    state = json.loads(path.read_text(encoding="utf-8"))
    checks = {
        "stage_range": state.get("stage_range") == "V88.01-V88.08",
        "status_pass": state.get("status") == "PASS",
        "state_ready": state.get("state") == "WEB_UI_V2_READY",
        "paper_only": state.get("paper_only") is True,
        "localhost_only": state.get("localhost_only") is True,
        "broker_write_disabled": state.get("broker_write_enabled") is False,
        "order_submission_disabled": state.get("order_submission_enabled") is False,
        "live_trading_disabled": state.get("live_trading_enabled") is False,
        "external_network_disabled": state.get("external_network_enabled") is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    payload = {
        "verification_stage": "V88.08",
        "verification_status": "PASS" if not failed else "FAIL",
        "state": state.get("state"),
        "sources": state.get("sources", {}),
        "checks": checks,
        "failed": failed,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
